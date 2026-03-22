---
name: Claude Dynamic UI Research
description: How Claude's app implements dynamic/generative UI mid-conversation — action buttons, forms, components. Full technical breakdown + implementation blueprint.
type: project
---

# Claude Dynamic UI — Research Report (2026-03-16)

## 1. How Claude.ai's Native Generative UI Works

### The Core Mechanism: `show_widget` + `read_me`
Claude's dynamic UI is **not** a special rendering engine — it's a **tool-call architecture**:

1. **`read_me` tool** — lazy-loads design guidelines on demand. Claude calls it first with `modules: ["chart", "interactive", "diagram", "mockup", "art"]` selecting only what's needed. Each module returns 17-22KB of design rules (typography, color, streaming-safe CSS patterns). This keeps the base system prompt lean — guidelines only injected when needed.

2. **`show_widget` tool** — takes a raw HTML fragment (no DOCTYPE, no html/body tags) and a title. Parameters:
   - `i_have_seen_read_me` (bool): gate ensuring guidelines were loaded
   - `title` (string, snake_case): widget identifier
   - `loading_messages` (1-4 strings): shown during rendering
   - `widget_code` (string): raw HTML/CSS/JS fragment

3. **DOM injection**: HTML is injected directly into the page DOM (NOT sandboxed iframe), allowing CSS variables to resolve and `sendPrompt()` callbacks to work. Scripts execute AFTER streaming completes.

4. **Streaming mechanism**: SSE (Server-Sent Events). Events: `widget_delta` (partial HTML chunk) + `widget_final` (complete). Client uses `morphdom` for DOM diffing — applies minimal patches rather than replacing the whole node, preventing flicker.

5. **Decision logic**: Claude autonomously decides when to use widgets vs text. The system prompt + tool descriptions guide this — no hardcoded routing. The model infers: "a chart would serve this better than a paragraph."

6. **Rule**: All explanatory text must be written OUTSIDE the tool call as normal response text. Tool output = pure visual element only.

### Design Modules (Lazy-Loaded)
| Module | Size | Purpose |
|---|---|---|
| interactive | 19KB | Sliders, metric cards, calculations |
| chart | 22KB | Chart.js configs, formatting |
| mockup | 19KB | UI components, forms, skeleton states |
| art | 17KB | SVG illustration, Canvas animation |
| diagram | 59KB | Flowcharts, architecture diagrams |

Source: github.com/Michaelliv/pi-generative-ui (reverse-engineered from claude.ai)

---

## 2. MCP Apps (External Interactive Connectors)

For third-party app integration (Figma, Slack, Asana etc.):

- MCP tools declare `_meta.ui.resourceUri` pointing to a `ui://` scheme resource
- Host fetches the resource (HTML/JS bundle) and renders it in a **double-sandboxed iframe**
- Communication: **JSON-RPC over postMessage** (bidirectional)
- Three operations from within the UI:
  1. `ontoolresult` — receive data from model
  2. `callServerTool(name, args)` — call MCP server back
  3. `updateModelContext(text)` — inject text into conversation context
- All UI-initiated tool calls require explicit user approval
- SDK: `@modelcontextprotocol/ext-apps`

This is for external apps. NOT what we want to build for OMS (that's iframe embedding of third-party services).

---

## 3. Vercel AI SDK — Generative UI Pattern

The cleanest open-source implementation:

### Architecture: Dual State
- **AI State** = serializable JSON. Conversation history + tool calls as JSON objects. Sent to/from model.
- **UI State** = client-only. React elements. Never sent to model. Rendered from AI State.

### streamUI Pattern (RSC approach)
```tsx
// Server action
const result = await streamUI({
  model: openai('gpt-4o'),
  prompt: userMessage,
  text: ({ content }) => <div>{content}</div>,  // fallback for text
  tools: {
    show_weather: {
      description: 'Show weather widget',
      inputSchema: z.object({ city: z.string() }),
      generate: async function*({ city }) {
        yield <Spinner />;  // loading state
        const data = await fetchWeather(city);
        return <WeatherCard data={data} />;
      }
    }
  }
});
```

### useChat Pattern (non-RSC, simpler — preferred for our OMS)
```tsx
// Message rendering with parts
message.parts.map((part) => {
  if (part.type === 'text') return <Markdown>{part.text}</Markdown>;
  if (part.type === 'tool-show_form') {
    if (part.state === 'input-available') return <FormSkeleton />;
    if (part.state === 'output-available') return <DynamicForm {...part.input} />;
  }
})
```

Tool names: `tool-${toolName}` — the part type is derived from the tool name.

### Key Hooks
- `useChat` — manages messages, streaming, send
- `InferUITool<typeof tool>` — TypeScript type safety on tool input/output
- `setMessages` — programmatically update messages (e.g., after form submit)

---

## 4. LangGraph Generative UI

For when Claude is orchestrating via LangGraph:
- Register components in `langgraph.json`
- Server emits: Python `push_ui_message()` / TS `typedUi()`
- Client: `useStream()` hook + `LoadExternalComponent` (fetches bundle from LangSmith)
- Components run in **shadow DOM** for style isolation
- `useStreamContext()` gives components access to conversation state
- Supports incremental streaming pushes

---

## 5. Open-Source Libraries

| Library | Approach | Best For |
|---|---|---|
| **assistant-ui** | Radix-style composable primitives. Renders tool calls as React components. Multi-backend. | Production chat UI, most flexible |
| **Vercel AI SDK** | useChat + parts + streamUI. First-class RSC support. | Next.js apps, our OMS stack |
| **LangGraph UI** | Shadow DOM components, server-pushed. | When using LangGraph as orchestrator |
| **Hashbrown** | Browser-side tool execution, WASM runtime. | Client-heavy agentic apps |
| **CopilotKit** | Copilot layer over any app. | Adding copilot to existing UIs |

---

## 6. Implementation Blueprint for OMS

**Context**: OMS is Next.js 15 at mev.otto.lk. We want the chat interface to dynamically render action buttons, option pickers, confirmation dialogs, and forms mid-conversation.

### Architecture Decision: Tool-to-Component Mapping

Use **Vercel AI SDK `useChat`** with tool call rendering (NOT streamUI/RSC — simpler, works with our existing setup).

### Step 1: Define UI Tools in the API Route

```typescript
// app/api/chat/route.ts
import { streamText, tool } from 'ai';
import { z } from 'zod';

const uiTools = {
  // Action button group
  show_options: tool({
    description: 'Show the user a set of action buttons to choose from',
    inputSchema: z.object({
      question: z.string(),
      options: z.array(z.object({
        label: z.string(),
        value: z.string(),
        variant: z.enum(['primary', 'secondary', 'danger']).optional()
      })),
      allowMultiple: z.boolean().default(false),
    }),
  }),

  // Dynamic form
  show_form: tool({
    description: 'Show a form for the user to fill in structured data',
    inputSchema: z.object({
      title: z.string(),
      fields: z.array(z.object({
        name: z.string(),
        label: z.string(),
        type: z.enum(['text', 'number', 'select', 'textarea', 'date']),
        required: z.boolean().default(false),
        options: z.array(z.string()).optional(),
        placeholder: z.string().optional(),
      })),
      submitLabel: z.string().default('Submit'),
    }),
  }),

  // Confirmation dialog
  confirm_action: tool({
    description: 'Ask the user to confirm a destructive or important action',
    inputSchema: z.object({
      title: z.string(),
      description: z.string(),
      confirmLabel: z.string().default('Confirm'),
      cancelLabel: z.string().default('Cancel'),
      variant: z.enum(['warning', 'danger', 'info']).default('warning'),
    }),
  }),

  // Data card / info display
  show_card: tool({
    description: 'Display structured data as a formatted card',
    inputSchema: z.object({
      title: z.string(),
      items: z.array(z.object({ label: z.string(), value: z.string() })),
      actions: z.array(z.object({ label: z.string(), action: z.string() })).optional(),
    }),
  }),
};

export async function POST(req: Request) {
  const { messages } = await req.json();
  const result = streamText({
    model: yourModel,
    system: SYSTEM_PROMPT,
    messages,
    tools: uiTools,
    maxSteps: 5,  // allow multi-step tool use
  });
  return result.toDataStreamResponse();
}
```

### Step 2: Tool-to-Component Map in Client

```tsx
// components/chat/ToolRenderer.tsx
import { ToolInvocation } from 'ai';
import { OptionsWidget, FormWidget, ConfirmWidget, CardWidget } from './widgets';

export function ToolRenderer({
  tool,
  onResult
}: {
  tool: ToolInvocation;
  onResult: (result: any) => void;
}) {
  // Show loading while tool is being called
  if (tool.state === 'partial-call') return <WidgetSkeleton />;
  if (tool.state === 'call') {
    switch (tool.toolName) {
      case 'show_options':
        return <OptionsWidget {...tool.args} onSelect={onResult} />;
      case 'show_form':
        return <FormWidget {...tool.args} onSubmit={onResult} />;
      case 'confirm_action':
        return <ConfirmWidget {...tool.args} onConfirm={onResult} onCancel={() => onResult(null)} />;
      case 'show_card':
        return <CardWidget {...tool.args} onAction={onResult} />;
    }
  }
  if (tool.state === 'result') {
    return <div className="text-xs text-muted">✓ Completed</div>;
  }
  return null;
}
```

### Step 3: Message Renderer

```tsx
// components/chat/MessageList.tsx
import { useChat } from 'ai/react';

export function MessageList() {
  const { messages, addToolResult } = useChat({
    api: '/api/chat',
    // Key: add tool results back into conversation
    onToolCall: async ({ toolCall }) => {
      // For client-side tool execution (optional)
      if (toolCall.toolName === 'show_options') {
        // Let OptionsWidget handle it via addToolResult
        return undefined;
      }
    }
  });

  return messages.map(message => (
    <div key={message.id}>
      {message.parts.map((part, i) => {
        if (part.type === 'text') {
          return <Markdown key={i}>{part.text}</Markdown>;
        }
        if (part.type.startsWith('tool-')) {
          return (
            <ToolRenderer
              key={i}
              tool={part}
              onResult={(result) => addToolResult({
                toolCallId: part.toolCallId,
                result
              })}
            />
          );
        }
      })}
    </div>
  ));
}
```

### Step 4: System Prompt for Tool Use

```
You are Otto, an AI assistant for the OMS dashboard.

When the user needs to make a choice between options, use show_options.
When you need structured input from the user, use show_form.
When you're about to take a destructive action, use confirm_action first.
When displaying project data or status, use show_card.

Rules:
- Write all explanatory text as normal text BEFORE tool calls
- Tool output = interactive element only, no text inside it
- After user responds to a widget, continue the conversation naturally
- If the user just wants a text answer, respond with text only — don't force widgets
```

### Step 5: Streaming + Design System

For native-feel streaming (like claude.ai's approach):
- Use **SSE** (built into AI SDK's `toDataStreamResponse()`)
- Use **morphdom** for incremental DOM updates if building custom renderer
- CSS variables from your design system work when using DOM injection (vs iframe)
- Keep animations: fade-in on widget appearance, skeleton while loading

### Architecture Summary

```
User message → API route → streamText() with UI tools
     ↓
Model decides: text response OR tool call (based on context + tool descriptions)
     ↓
Tool call streamed → client receives via useChat parts array
     ↓
ToolRenderer maps toolName → React component
     ↓
User interacts → addToolResult() sends response back to model
     ↓
Model continues conversation with tool result in context
```

---

## 7. Complexity Tiers

| Tier | Approach | Effort | Quality |
|---|---|---|---|
| **Tier 1** (MVP) | useChat + parts + 4-5 UI tools + simple components | 1 day | Good |
| **Tier 2** (Claude-like) | Add lazy-loaded design guidelines, morphdom streaming, CSS variables | 2-3 days | Excellent |
| **Tier 3** (Full MCP) | MCP Apps spec, iframe sandboxing, postMessage JSON-RPC | 1 week | Enterprise |

**Recommendation for OMS**: Tier 1 MVP first. Tier 2 for the "Claude-like feel."

---

## 8. Key Files to Reference (Open Source)

- `github.com/Michaelliv/pi-generative-ui` — reverse-engineered Claude UI guidelines + show_widget impl
- `github.com/assistant-ui/assistant-ui` — production-ready composable chat primitives
- `ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces` — official guide
- `ai-sdk.dev/docs/ai-sdk-rsc/streaming-react-components` — RSC streaming pattern

**Why:** Mev wants to know the architecture in order to build it for the OMS or similar interfaces.
**How to apply:** This is our blueprint. Tier 1 implementation can start immediately with useChat + 4 tool types + ToolRenderer.

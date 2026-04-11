// Manually syntax-highlighted TypeScript code block
// Uses CSS classes defined in globals.css for coloring

type Token = { type: string; text: string };
type Line = Token[];

const codeLines: Line[] = [
  [
    { type: 'keyword', text: 'import' },
    { type: 'plain', text: ' { ' },
    { type: 'type', text: 'ZkPresenceClient' },
    { type: 'plain', text: ', ' },
    { type: 'type', text: 'AttestationMode' },
    { type: 'plain', text: ' } ' },
    { type: 'keyword', text: 'from' },
    { type: 'string', text: " '@zkpresence/sdk'" },
    { type: 'punctuation', text: ';' },
  ],
  [],
  [
    { type: 'keyword', text: 'const' },
    { type: 'plain', text: ' ' },
    { type: 'variable', text: 'client' },
    { type: 'plain', text: ' = ' },
    { type: 'keyword', text: 'new' },
    { type: 'plain', text: ' ' },
    { type: 'function', text: 'ZkPresenceClient' },
    { type: 'punctuation', text: '({' },
  ],
  [
    { type: 'property', text: '  chainId' },
    { type: 'punctuation', text: ': ' },
    { type: 'number', text: '8453' },
    { type: 'punctuation', text: ',' },
    { type: 'comment', text: ' // Base' },
  ],
  [
    { type: 'property', text: '  contractAddress' },
    { type: 'punctuation', text: ': ' },
    { type: 'string', text: "'0x...'" },
    { type: 'punctuation', text: ',' },
  ],
  [
    { type: 'property', text: '  apiKey' },
    { type: 'punctuation', text: ': ' },
    { type: 'variable', text: 'process' },
    { type: 'punctuation', text: '.' },
    { type: 'property', text: 'env' },
    { type: 'punctuation', text: '.' },
    { type: 'property', text: 'ZKPRESENCE_API_KEY' },
    { type: 'punctuation', text: ',' },
  ],
  [{ type: 'punctuation', text: '});' }],
  [],
  [{ type: 'comment', text: '// Attendee proves they were at the event' }],
  [
    { type: 'keyword', text: 'const' },
    { type: 'plain', text: ' ' },
    { type: 'variable', text: 'proof' },
    { type: 'plain', text: ' = ' },
    { type: 'keyword', text: 'await' },
    { type: 'plain', text: ' ' },
    { type: 'variable', text: 'client' },
    { type: 'punctuation', text: '.' },
    { type: 'function', text: 'prove' },
    { type: 'punctuation', text: '({' },
  ],
  [
    { type: 'property', text: '  eventId' },
    { type: 'punctuation', text: ': ' },
    { type: 'string', text: "'eth-denver-2026'" },
    { type: 'punctuation', text: ',' },
  ],
  [
    { type: 'property', text: '  mode' },
    { type: 'punctuation', text: ': ' },
    { type: 'type', text: 'AttestationMode' },
    { type: 'punctuation', text: '.' },
    { type: 'property', text: 'QR' },
    { type: 'punctuation', text: ',' },
  ],
  [
    { type: 'property', text: '  userSecret' },
    { type: 'punctuation', text: ': ' },
    { type: 'keyword', text: 'await' },
    { type: 'plain', text: ' ' },
    { type: 'variable', text: 'client' },
    { type: 'punctuation', text: '.' },
    { type: 'function', text: 'loadOrGenerateSecret' },
    { type: 'punctuation', text: '(),' },
  ],
  [
    { type: 'property', text: '  attestation' },
    { type: 'punctuation', text: ': ' },
    { type: 'variable', text: 'scannedQrPayload' },
    { type: 'punctuation', text: ',' },
  ],
  [{ type: 'punctuation', text: '});' }],
  [],
  [{ type: 'comment', text: '// Submit on-chain' }],
  [
    { type: 'keyword', text: 'const' },
    { type: 'plain', text: ' ' },
    { type: 'variable', text: 'tx' },
    { type: 'plain', text: ' = ' },
    { type: 'keyword', text: 'await' },
    { type: 'plain', text: ' ' },
    { type: 'variable', text: 'client' },
    { type: 'punctuation', text: '.' },
    { type: 'function', text: 'submitProof' },
    { type: 'punctuation', text: '(' },
    { type: 'variable', text: 'proof' },
    { type: 'punctuation', text: ');' },
  ],
  [
    { type: 'variable', text: 'console' },
    { type: 'punctuation', text: '.' },
    { type: 'function', text: 'log' },
    { type: 'punctuation', text: '(' },
    { type: 'string', text: "'Attendance verified:'" },
    { type: 'punctuation', text: ', ' },
    { type: 'variable', text: 'tx' },
    { type: 'punctuation', text: '.' },
    { type: 'property', text: 'hash' },
    { type: 'punctuation', text: ');' },
  ],
];

function CodeLine({ tokens }: { tokens: Token[] }) {
  if (tokens.length === 0) {
    return <div style={{ height: '1.7em' }} />;
  }
  return (
    <div>
      {tokens.map((token, i) => (
        <span key={i} className={`tok-${token.type}`}>
          {token.text}
        </span>
      ))}
    </div>
  );
}

export default function CodeSnippet() {
  return (
    <section
      id="docs"
      className="py-24 px-6 relative"
      aria-labelledby="code-snippet-heading"
    >
      {/* Background separator */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        aria-hidden="true"
        style={{ background: 'linear-gradient(to right, transparent, rgba(6,182,212,0.2), transparent)' }}
      />

      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <p
            className="text-xs font-semibold tracking-widest uppercase mb-3"
            style={{ color: 'var(--accent-cyan)' }}
          >
            SDK Integration
          </p>
          <h2
            id="code-snippet-heading"
            className="text-3xl md:text-4xl font-bold tracking-tight mb-4"
            style={{ fontFamily: 'Syne, sans-serif' }}
          >
            Integrate in minutes.
          </h2>
          <p style={{ color: 'var(--text-secondary)' }}>
            Self-host or use our managed API. Type-safe SDK for TypeScript and Rust.
          </p>
        </div>

        {/* Code block */}
        <div className="code-block">
          {/* Header bar */}
          <div className="code-block-header">
            <div className="code-dot" style={{ background: '#ff5f57' }} />
            <div className="code-dot" style={{ background: '#febc2e' }} />
            <div className="code-dot" style={{ background: '#28c840' }} />
            <span
              className="ml-2 text-xs font-mono"
              style={{ color: 'var(--text-muted)', fontFamily: 'DM Mono, monospace' }}
            >
              prove-attendance.ts
            </span>
            <div className="flex-1" />
            {/* Copy indicator */}
            <div className="flex items-center gap-1.5">
              <div
                className="w-1.5 h-1.5 rounded-full animate-flow-node-cyan"
                style={{ background: 'var(--accent-cyan)' }}
              />
              <span
                className="text-xs"
                style={{ color: 'var(--text-muted)', fontFamily: 'DM Mono, monospace' }}
              >
                TypeScript
              </span>
            </div>
          </div>

          {/* Code content */}
          <div className="code-content" role="region" aria-label="Code example">
            {codeLines.map((line, i) => (
              <CodeLine key={i} tokens={line} />
            ))}
          </div>
        </div>

        {/* Footer links */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6">
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            MIT licensed. Works with any EVM-compatible chain.
          </p>
          <a
            href="#docs"
            className="text-sm flex items-center gap-1.5 transition-colors duration-200 font-medium"
            style={{ color: 'var(--accent-cyan)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-cyan-light)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--accent-cyan)')}
          >
            View full docs
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>

        {/* Install command */}
        <div
          className="mt-8 rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border-subtle)' }}
        >
          <div
            className="px-5 py-3 flex items-center gap-3"
            style={{ background: 'rgba(255,255,255,0.02)' }}
          >
            <span
              className="text-xs"
              style={{ color: 'var(--text-muted)', fontFamily: 'DM Mono, monospace' }}
            >
              $
            </span>
            <code
              className="text-sm flex-1"
              style={{ color: 'rgba(255,255,255,0.8)', fontFamily: 'DM Mono, monospace' }}
            >
              npm install @zkpresence/sdk
            </code>
            <div
              className="flex items-center gap-1.5 text-xs px-2 py-1 rounded"
              style={{ color: 'var(--accent-purple-light)', background: 'rgba(124,58,237,0.08)' }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              MIT
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

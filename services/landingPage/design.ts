/**
 * Design Synthesis Engine for Landing Page Generation
 *
 * Parses /mnt/media/prompts.md into a structured catalog of 33 design systems,
 * then uses LLM to select and customize the best design for a given business.
 *
 * Exports:
 *   designSynthesizer(researchData, competitorData) → DesignDecisions
 *   copyGenerator(businessData, designDecisions) → SectionCopy
 *   parseDesignCatalog() → DesignEntry[]
 *   storeDesignDecisions(landingPageId, decisions) → void
 */

import { readFileSync } from "fs";
import OpenAI from "openai";
import pg from "pg";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FontSpec {
  family: string;
  weight: number;
  style: string;
}

export interface ColorPalette {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
  muted: string;
}

export interface SectionSpec {
  type: string;
  name: string;
  layout: string;
  notes: string;
}

export interface AnimationSpec {
  style: string;
  easing: string;
  duration: string;
  scroll_reveal: boolean;
}

export interface DesignDecisions {
  selected_design_id: string;
  design_name: string;
  fonts: { heading: FontSpec; body: FontSpec; accent: FontSpec };
  colors: ColorPalette;
  ui_style: string;
  color_mode: "light" | "dark";
  sections: SectionSpec[];
  imagery_style: string;
  copy_tone: string;
  animations: AnimationSpec;
  special_components: string[];
  rationale: string;
  _source_spec?: string;
  _source_sections?: string[];
  _source_components?: string[];
  _source_notes?: string;
  _fallback?: boolean;
}

export interface CtaSpec {
  text: string;
  action: string;
}

export interface CopyItem {
  title: string;
  description: string;
  icon_hint: string;
}

export interface CopySection {
  type: string;
  heading: string;
  subheading: string | null;
  body: string | null;
  items: CopyItem[];
}

export interface Testimonial {
  quote: string;
  author: string;
  role: string;
}

export interface StatItem {
  value: string;
  label: string;
}

export interface SectionCopy {
  headline: string;
  subheadline: string;
  cta_primary: CtaSpec;
  cta_secondary: CtaSpec;
  sections: CopySection[];
  social_proof: {
    headline: string;
    testimonials: Testimonial[];
    stats: StatItem[];
  };
  footer: { tagline: string; cta: string };
  meta: {
    page_title: string;
    meta_description: string;
    og_title: string;
    og_description: string;
  };
  _fallback?: boolean;
}

export interface DesignEntry {
  id: string;
  summary: string;
  style_description: string;
  ui_style: string;
  color_mode: string;
  copy_tone: string;
  fonts: string[];
  colors: Record<string, string>;
  sections: string[];
  special_components: string[];
  special_notes: string;
  raw_spec: string;
}

export interface ResearchData {
  business_name?: string;
  industry?: string;
  pricing_tier?: string;
  tone_of_voice?: string;
  brand_colors?: string[];
  target_audience?: string;
  differentiator?: string;
  value_proposition?: string;
  products_services?: string[];
  tagline?: string;
  notable_reviews_or_press?: string[];
  [key: string]: unknown;
}

export interface CompetitorData {
  competitors?: Array<{ name?: string; visual_style?: string; [k: string]: unknown }>;
  positioning_gaps?: string[];
  recommended_angles?: string[];
  visual_direction_notes?: string;
  messaging_direction_notes?: string;
  [key: string]: unknown;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PROMPTS_PATH = "/mnt/media/prompts.md";

const BANNED_FONTS = new Set([
  "Inter",
  "Roboto",
  "Arial",
  "Open Sans",
  "Lato",
  "Montserrat",
  "Poppins",
  "Space Grotesk",
]);

const KNOWN_FONTS = new Set([
  "Clash Display",
  "Clash Grotesk",
  "Satoshi",
  "General Sans",
  "Anton",
  "Plus Jakarta Sans",
  "League Spartan",
  "JetBrains Mono",
  "Geist Mono",
  "DM Serif Display",
  "Playfair Display",
  "Outfit",
  "Reenie Beanie",
  "Aileron",
  "Inter Tight",
  "Lora",
  "ZTNature",
  "Aspekta",
  "Archivo Black",
  "Space Mono",
  "Instrument Sans",
  "Newsreader",
  "Manrope",
]);

const NON_FONT_WORDS = new Set([
  "Echo Stack",
  "Read More",
  "View Case",
  "Quick View",
  "Raw",
  "New",
  "Most Popular",
  "Join Digest",
  "Get Access",
  "Enter",
  "Free Access",
  "Super Travel",
  "Season",
  "THE FLUX WAY",
  "THE OLD WAY",
  "SUPER",
  "SELECTED WORKS",
  "WORKS",
  "GET ACCESS",
  "Scroll Down",
  "System Online",
  "Core Capabilities",
  "System Analysis",
  "CREATE",
  "NEW DROPS",
  "Digital Minimalism",
  "Digital Naturalism",
  "Forest and Sage",
  "Forest",
  "Frameworks",
  "Capabilities",
  "Socials",
  "Contact",
  "Explore",
  "Breathe",
  "Neon Velocity",
  "Noir",
  "Cyber Serif",
  "Cinematic Style",
  "Modern Obsidian",
  "Midnight Editorial",
  "Laser Button",
  "Technical Minimalist",
  "Poster Modernist",
  "Kinetic Orange",
  "Shimmer Border",
  "Grid Matrix",
  "Label Sidebar",
  "WHY DIFFERENT",
  "OUTERWEAR",
  "Send",
  "Join",
  "Metadata Bar",
  "Folder",
  "Social",
  "Acid",
  "LIVE",
  "AM",
  "PM",
  "AI label",
  "View",
  "Let",
]);

// ─── OpenAI Client ────────────────────────────────────────────────────────────

function getOpenAI(): OpenAI {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY not set");
  }
  return new OpenAI({ apiKey });
}

// ─── DB Pool ──────────────────────────────────────────────────────────────────

function getPool(): pg.Pool {
  return new pg.Pool({
    host: process.env.POSTGRES_HOST ?? "localhost",
    port: parseInt(process.env.POSTGRES_PORT ?? "5432", 10),
    user: process.env.POSTGRES_USER ?? "otto",
    password: process.env.POSTGRES_PASSWORD ?? process.env.PGPASSWORD,
    database: process.env.POSTGRES_DB ?? "memory",
  });
}

// ─── LLM Helpers ──────────────────────────────────────────────────────────────

async function llmChat(
  systemPrompt: string,
  userPrompt: string,
  maxTokens: number = 2000,
  temperature: number = 0.3
): Promise<string> {
  const client = getOpenAI();
  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    max_tokens: maxTokens,
    temperature,
  });
  return response.choices[0]?.message?.content ?? "";
}

function extractJson<T>(text: string): T | null {
  // Try direct parse
  try {
    return JSON.parse(text) as T;
  } catch {
    // noop
  }
  // Try extracting from markdown code fences
  const fenceMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (fenceMatch) {
    try {
      return JSON.parse(fenceMatch[1]) as T;
    } catch {
      // noop
    }
  }
  // Try finding first { ... } block
  const braceMatch = text.match(/\{[\s\S]*\}/);
  if (braceMatch) {
    try {
      return JSON.parse(braceMatch[0]) as T;
    } catch {
      // noop
    }
  }
  return null;
}

// ─── Design Catalog Parser ────────────────────────────────────────────────────

function extractFonts(text: string): string[] {
  const found: string[] = [];
  const seen = new Set<string>();

  // First pass: known fonts
  for (const font of KNOWN_FONTS) {
    if (text.includes(font) && !seen.has(font)) {
      found.push(font);
      seen.add(font);
    }
  }

  // Second pass: quoted font names
  const quoted = text.matchAll(/['"]([A-Z][A-Za-z\s]+?)['"]/g);
  for (const m of quoted) {
    const f = m[1].trim();
    if (
      !seen.has(f) &&
      !NON_FONT_WORDS.has(f) &&
      f.length < 25 &&
      f.includes(" ") &&
      /[A-Z]/.test(f.slice(1))
    ) {
      seen.add(f);
      found.push(f);
    }
  }
  return found;
}

function extractColors(text: string): Record<string, string> {
  const colors: Record<string, string> = {};
  const roleNames = [
    "background",
    "primary_text",
    "accent",
    "secondary",
    "muted",
    "border",
    "highlight",
  ];
  let idx = 0;

  const pattern = /(?:(\w[\w\s/]*?)[:=]\s*)?`?(#[0-9A-Fa-f]{6})\b`?(?:\s*\(([^)]+)\))?/g;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    const rawLabel = (match[1] || match[3] || "").trim().toLowerCase();
    let key = rawLabel.replace(/[^a-z0-9_ ]/g, "").trim().replace(/ /g, "_");
    if (!key || key in colors) {
      key = idx < roleNames.length ? roleNames[idx] : `color_${idx}`;
      idx++;
    }
    if (match[2]) {
      colors[key] = match[2];
    }
  }
  return colors;
}

function extractSections(text: string): string[] {
  const layoutMatch = text.match(
    /# Layout & Structure\n([\s\S]*?)(?=\n# (?!#)|$)/
  );
  if (!layoutMatch) return [];
  const sections = layoutMatch[1].matchAll(/^## (.+)$/gm);
  return Array.from(sections, (m) => m[1]);
}

function extractSpecialComponents(text: string): string[] {
  const compsMatch = text.match(
    /# Special Components\n([\s\S]*?)(?=\n# (?!#)|$)/
  );
  if (!compsMatch) return [];
  return Array.from(compsMatch[1].matchAll(/^## (.+)$/gm), (m) => m[1]);
}

function extractSpecialNotes(text: string): string {
  const notesMatch = text.match(
    /# Special Notes\n([\s\S]+?)(?=\nDESIGN \d|$)/
  );
  return notesMatch ? notesMatch[1].trim() : "";
}

function classifyStyle(summary: string, styleText: string): string {
  const combined = (summary + " " + styleText).toLowerCase();
  if (combined.includes("brutalist") || combined.includes("brutal")) {
    if (combined.includes("luxury") || combined.includes("fashion"))
      return "luxury-brutalist";
    if (combined.includes("lite") || combined.includes("saas"))
      return "brutalist-lite";
    return "brutalist";
  }
  if (combined.includes("minimal") && (combined.includes("dark") || combined.includes("obsidian")))
    return "dark-minimal";
  if (combined.includes("minimal")) return "minimal";
  if (combined.includes("editorial")) return "editorial";
  if (combined.includes("glass") || combined.includes("glassmorphism"))
    return "glassmorphic";
  if (combined.includes("wellness") || combined.includes("soft") || combined.includes("pastel"))
    return "soft-organic";
  if (combined.includes("neon") || combined.includes("cyber") || combined.includes("futuristic"))
    return "futuristic";
  if (combined.includes("luxury") || combined.includes("premium"))
    return "luxury";
  if (combined.includes("corporate") || combined.includes("technical"))
    return "technical";
  if (combined.includes("cinematic")) return "cinematic";
  if (combined.includes("playful") || combined.includes("bold")) return "bold";
  return "modern";
}

function classifyTone(summary: string, styleText: string): string {
  const combined = (summary + " " + styleText).toLowerCase();
  if (combined.includes("luxury") || combined.includes("premium") || combined.includes("fashion"))
    return "refined-authoritative";
  if (combined.includes("brutalist") || combined.includes("aggressive") || combined.includes("raw"))
    return "bold-direct";
  if (combined.includes("wellness") || combined.includes("soft") || combined.includes("organic"))
    return "warm-conversational";
  if (combined.includes("technical") || combined.includes("architectural"))
    return "precise-technical";
  if (combined.includes("cinematic") || combined.includes("editorial"))
    return "narrative-dramatic";
  if (combined.includes("neon") || combined.includes("velocity") || combined.includes("kinetic"))
    return "urgent-energetic";
  if (combined.includes("saas") || combined.includes("modern"))
    return "clear-confident";
  return "professional";
}

function classifyColorMode(colors: Record<string, string>): string {
  const bgKey = Object.keys(colors).find(
    (k) => k.includes("background") || k.includes("bg") || k.includes("base")
  );
  if (bgKey) {
    const bg = colors[bgKey].toLowerCase();
    const r = parseInt(bg.slice(1, 3), 16);
    const g = parseInt(bg.slice(3, 5), 16);
    const b = parseInt(bg.slice(5, 7), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance < 0.3 ? "dark" : "light";
  }
  return "light";
}

/**
 * Parse /mnt/media/prompts.md into a structured array of design system entries.
 */
export function parseDesignCatalog(
  path: string = PROMPTS_PATH
): DesignEntry[] {
  let content: string;
  try {
    content = readFileSync(path, "utf-8");
  } catch (err) {
    console.error(`Failed to read prompts file: ${path}`, err);
    return [];
  }

  const blocks = content.split(/\n(?=DESIGN \d+)/);
  const catalog: DesignEntry[] = [];

  for (const block of blocks) {
    const idMatch = block.match(/^DESIGN (\d+)/);
    if (!idMatch) continue;

    const designId = `DESIGN_${idMatch[1].padStart(2, "0")}`;

    const summaryMatch = block.match(/# Summary\n\n(.+?)(?=\n#)/s);
    const summary = summaryMatch ? summaryMatch[1].trim() : "";

    const styleMatch = block.match(/# Style\n\n(.+?)(?=\n## Spec|\n# )/s);
    const styleDesc = styleMatch ? styleMatch[1].trim() : "";

    const specMatch = block.match(/## Spec\n\n(.+?)(?=\n# )/s);
    const rawSpec = specMatch ? specMatch[1].trim().slice(0, 2000) : "";

    const fonts = extractFonts(block);
    const colors = extractColors(rawSpec || block.slice(0, 3000));
    const sections = extractSections(block);
    const components = extractSpecialComponents(block);
    const notes = extractSpecialNotes(block);

    const uiStyle = classifyStyle(summary, styleDesc);
    const copyTone = classifyTone(summary, styleDesc);
    const colorMode = classifyColorMode(colors);

    catalog.push({
      id: designId,
      summary,
      style_description: styleDesc,
      ui_style: uiStyle,
      color_mode: colorMode,
      copy_tone: copyTone,
      fonts,
      colors,
      sections,
      special_components: components,
      special_notes: notes,
      raw_spec: rawSpec,
    });
  }

  console.log(`Parsed ${catalog.length} design systems from ${path}`);
  return catalog;
}

// Module-level cache
let catalogCache: DesignEntry[] | null = null;

function getCatalog(): DesignEntry[] {
  if (!catalogCache) {
    catalogCache = parseDesignCatalog();
  }
  return catalogCache;
}

function getCatalogSummaries(): string {
  const catalog = getCatalog();
  return catalog
    .map((d) => {
      const fontsStr = d.fonts.slice(0, 3).join(", ") || "unspecified";
      const topColors = Object.values(d.colors).slice(0, 4);
      const colorsStr = topColors.join(" ") || "unspecified";
      return (
        `- ${d.id}: ${d.summary.slice(0, 120)}... ` +
        `| Style: ${d.ui_style} | Mode: ${d.color_mode} ` +
        `| Fonts: ${fontsStr} | Colors: ${colorsStr} ` +
        `| Sections: ${d.sections.slice(0, 5).join(", ")}`
      );
    })
    .join("\n");
}

function getDesignById(designId: string): DesignEntry | undefined {
  return getCatalog().find((d) => d.id === designId);
}

// ─── Design Synthesizer ───────────────────────────────────────────────────────

/**
 * Synthesize design decisions from research and competitor data.
 *
 * Uses the prompts.md design catalog + LLM to select fonts, colors,
 * UI style, sections, imagery style, copy tone, and animations.
 *
 * @returns Structured DesignDecisions object ready for HTML generation.
 */
export async function designSynthesizer(
  researchData: ResearchData,
  competitorData: CompetitorData
): Promise<DesignDecisions> {
  const catalogSummary = getCatalogSummaries();
  const catalog = getCatalog();

  const businessName = researchData.business_name ?? "Unknown Business";
  const industry = researchData.industry ?? "general";
  const pricingTier = researchData.pricing_tier ?? "mid";
  const tone = researchData.tone_of_voice ?? "professional";
  const existingColors = researchData.brand_colors ?? [];
  const targetAudience = researchData.target_audience ?? "general audience";
  const differentiator = researchData.differentiator ?? "";

  // Competitor visual directions
  const competitorStyles = (competitorData.competitors ?? [])
    .filter((c): c is { name?: string; visual_style?: string } => typeof c === "object")
    .map((c) => `- ${c.name ?? "?"}: ${c.visual_style ?? "unknown"}`);
  const competitorVisual =
    competitorStyles.length > 0
      ? competitorStyles.join("\n")
      : "No competitor data available";

  const positioningGaps = competitorData.positioning_gaps ?? [];
  const recommendedAngles = competitorData.recommended_angles ?? [];

  const systemPrompt = `You are an expert web designer selecting a design system for a landing page.

You have a catalog of ${catalog.length} proven design systems. Your job is to select the BEST one
for this business and customize it. Consider:

1. INDUSTRY FIT — A law firm needs authority (technical/editorial), a wellness brand needs warmth (soft-organic)
2. AUDIENCE MATCH — Gen Z prefers bold/futuristic, professionals prefer minimal/editorial
3. COMPETITOR DIFFERENTIATION — If competitors all use dark themes, consider light. Stand out.
4. BRAND ALIGNMENT — Respect existing brand colors if strong, otherwise propose fresh palette
5. PRICING TIER — Premium businesses need luxury aesthetics, budget businesses need clean/clear

BANNED FONTS (never select these): ${Array.from(BANNED_FONTS).join(", ")}

DESIGN CATALOG:
${catalogSummary}`;

  const userPrompt = `Select and customize a design system for this landing page:

BUSINESS: ${businessName}
INDUSTRY: ${industry}
PRICING TIER: ${pricingTier}
TONE: ${tone}
EXISTING BRAND COLORS: ${JSON.stringify(existingColors)}
TARGET AUDIENCE: ${targetAudience}
DIFFERENTIATOR: ${differentiator}

COMPETITOR VISUAL STYLES:
${competitorVisual}

POSITIONING GAPS: ${JSON.stringify(positioningGaps)}
RECOMMENDED ANGLES: ${JSON.stringify(recommendedAngles)}
VISUAL DIRECTION NOTES: ${competitorData.visual_direction_notes ?? "none"}
MESSAGING DIRECTION NOTES: ${competitorData.messaging_direction_notes ?? "none"}

Return a JSON object with these exact keys:
{
    "selected_design_id": "DESIGN_XX",
    "design_name": "short name for this customized design",
    "fonts": {
        "heading": {"family": "Font Name", "weight": 700, "style": "normal"},
        "body": {"family": "Font Name", "weight": 400, "style": "normal"},
        "accent": {"family": "Font Name", "weight": 500, "style": "normal"}
    },
    "colors": {
        "primary": "#hex",
        "secondary": "#hex",
        "accent": "#hex",
        "background": "#hex",
        "text": "#hex",
        "muted": "#hex"
    },
    "ui_style": "category",
    "color_mode": "light|dark",
    "sections": [
        {"type": "hero", "name": "Hero", "layout": "layout_type", "notes": "specifics"},
        ... (6-10 sections in recommended order)
    ],
    "imagery_style": "description",
    "copy_tone": "description of writing voice",
    "animations": {
        "style": "smooth|snappy|weighted|minimal",
        "easing": "cubic-bezier(x,y,z,w)",
        "duration": "Xms",
        "scroll_reveal": true
    },
    "special_components": ["list of 2-4 signature components"],
    "rationale": "2-3 sentences explaining why this design fits"
}

IMPORTANT:
- Do NOT use banned fonts
- If existing brand colors are strong, incorporate them into the palette
- Select 6-10 sections appropriate for this business type
- Ensure the design DIFFERENTIATES from competitors
- Return ONLY valid JSON, no markdown fences`;

  let decisions: DesignDecisions;

  try {
    const response = await llmChat(systemPrompt, userPrompt, 2000, 0.3);
    const parsed = extractJson<DesignDecisions>(response);
    if (!parsed) {
      console.error("LLM failed to return valid design decisions JSON");
      return fallbackDesign();
    }
    decisions = parsed;
  } catch (err) {
    console.error("LLM call failed for design synthesis:", err);
    return fallbackDesign();
  }

  // Post-process: validate and enrich
  decisions = validateDecisions(decisions);

  // Enrich with raw spec from selected design
  const selectedDesign = getDesignById(decisions.selected_design_id);
  if (selectedDesign) {
    decisions._source_spec = selectedDesign.raw_spec;
    decisions._source_sections = selectedDesign.sections;
    decisions._source_components = selectedDesign.special_components;
    decisions._source_notes = selectedDesign.special_notes;
  }

  console.log(
    `Design synthesized for ${businessName}: ${decisions.design_name} ` +
      `(base: ${decisions.selected_design_id}, style: ${decisions.ui_style})`
  );

  return decisions;
}

// ─── Copy Generator ───────────────────────────────────────────────────────────

/**
 * Generate all section copy for the landing page using LLM.
 *
 * @returns Structured SectionCopy with headline, sections, CTAs, meta tags, etc.
 */
export async function copyGenerator(
  businessData: ResearchData,
  designDecisions: DesignDecisions
): Promise<SectionCopy> {
  const businessName = businessData.business_name ?? "Unknown Business";
  const industry = businessData.industry ?? "general";
  const valueProp = businessData.value_proposition ?? "";
  const products = businessData.products_services ?? [];
  const differentiator = businessData.differentiator ?? "";
  const targetAudience = businessData.target_audience ?? "general audience";
  const tagline = businessData.tagline ?? "";
  const reviews = (businessData.notable_reviews_or_press ?? []).slice(0, 3);

  const copyTone = designDecisions.copy_tone ?? "professional";
  const sections = designDecisions.sections ?? [];
  const uiStyle = designDecisions.ui_style ?? "modern";

  const sectionList = sections
    .map((s) =>
      typeof s === "object"
        ? `- ${s.type}: ${s.name} (${s.layout})`
        : `- ${s}`
    )
    .join("\n");
  const sectionsStr = sectionList || "hero, features, social_proof, cta";

  const systemPrompt = `You are an expert landing page copywriter. Write compelling, conversion-optimized copy
for a landing page. Your writing voice must match: ${copyTone}

Guidelines:
- Headlines should be punchy, specific, and benefit-driven (not generic)
- Subheadlines should expand on the headline with a supporting detail
- Feature descriptions should focus on BENEFITS, not just features
- CTAs should be action-oriented and specific (not just "Learn More")
- Social proof should feel authentic and specific
- Avoid cliches: "revolutionize", "cutting-edge", "world-class", "synergy"
- Match the UI style: ${uiStyle} — e.g., brutalist copy is direct/raw, luxury is refined
- Keep headline under 10 words, subheadline under 25 words
- SEO meta description: 150-160 chars, include primary keyword naturally`;

  const userPrompt = `Write all copy for the ${businessName} landing page.

BUSINESS: ${businessName}
INDUSTRY: ${industry}
VALUE PROPOSITION: ${valueProp}
PRODUCTS/SERVICES: ${JSON.stringify(products)}
DIFFERENTIATOR: ${differentiator}
TARGET AUDIENCE: ${targetAudience}
EXISTING TAGLINE: ${tagline}
REVIEWS/PRESS: ${reviews.length > 0 ? JSON.stringify(reviews) : "none"}

SECTIONS TO WRITE COPY FOR:
${sectionsStr}

Return a JSON object:
{
    "headline": "primary hero headline (max 10 words)",
    "subheadline": "supporting text (max 25 words)",
    "cta_primary": {"text": "button text", "action": "#signup or url"},
    "cta_secondary": {"text": "secondary link text", "action": "#learn-more"},
    "sections": [
        {
            "type": "section_type",
            "heading": "section heading",
            "subheading": "optional subheading or null",
            "body": "body text if applicable or null",
            "items": [
                {"title": "item title", "description": "1-2 sentence description", "icon_hint": "suggested icon name"}
            ]
        }
    ],
    "social_proof": {
        "headline": "social proof section heading",
        "testimonials": [
            {"quote": "testimonial text (2-3 sentences)", "author": "First L.", "role": "Title, Company"}
        ],
        "stats": [
            {"value": "100+", "label": "metric name"}
        ]
    },
    "footer": {
        "tagline": "short footer tagline",
        "cta": "footer CTA text"
    },
    "meta": {
        "page_title": "SEO title (50-60 chars)",
        "meta_description": "SEO meta description (150-160 chars)",
        "og_title": "social share title",
        "og_description": "social share description (under 100 chars)"
    }
}

Write copy for EVERY section listed above. Each section needs heading + items or body.
Return ONLY valid JSON, no markdown fences.`;

  let copyData: SectionCopy;

  try {
    const response = await llmChat(systemPrompt, userPrompt, 3000, 0.5);
    const parsed = extractJson<SectionCopy>(response);
    if (!parsed) {
      console.error("LLM failed to return valid copy JSON");
      return fallbackCopy(businessData);
    }
    copyData = parsed;
  } catch (err) {
    console.error("LLM call failed for copy generation:", err);
    return fallbackCopy(businessData);
  }

  // Post-process: ensure all required fields
  copyData = validateCopy(copyData, businessData);

  console.log(
    `Copy generated for ${businessName}: ` +
      `${(copyData.sections ?? []).length} sections, ` +
      `${(copyData.social_proof?.testimonials ?? []).length} testimonials`
  );

  return copyData;
}

// ─── DB Storage ───────────────────────────────────────────────────────────────

/**
 * Store design decisions in the landing_pages.design_decisions JSONB column.
 */
export async function storeDesignDecisions(
  landingPageId: string,
  decisions: DesignDecisions
): Promise<void> {
  const pool = getPool();
  try {
    await pool.query(
      `UPDATE landing_pages
       SET design_decisions = $1::jsonb,
           status = 'designing',
           updated_at = NOW()
       WHERE id = $2`,
      [JSON.stringify(decisions), landingPageId]
    );
    console.log(`Design decisions stored for landing page ${landingPageId}`);
  } finally {
    await pool.end();
  }
}

/**
 * Store generated copy in the landing_pages.copy_data JSONB column.
 */
export async function storeCopyData(
  landingPageId: string,
  copyData: SectionCopy
): Promise<void> {
  const pool = getPool();
  try {
    await pool.query(
      `UPDATE landing_pages
       SET copy_data = $1::jsonb,
           updated_at = NOW()
       WHERE id = $2`,
      [JSON.stringify(copyData), landingPageId]
    );
    console.log(`Copy data stored for landing page ${landingPageId}`);
  } finally {
    await pool.end();
  }
}

// ─── Validation Helpers ───────────────────────────────────────────────────────

function validateDecisions(decisions: Partial<DesignDecisions>): DesignDecisions {
  const defaults: Partial<DesignDecisions> = {
    selected_design_id: "DESIGN_06",
    design_name: "Custom Design",
    ui_style: "modern",
    color_mode: "light",
    imagery_style: "minimal photography",
    copy_tone: "professional",
    rationale: "Default selection",
  };

  for (const [key, val] of Object.entries(defaults)) {
    if (!(key in decisions)) {
      (decisions as Record<string, unknown>)[key] = val;
    }
  }

  // Validate fonts
  if (!decisions.fonts || typeof decisions.fonts !== "object") {
    decisions.fonts = {
      heading: { family: "Clash Display", weight: 700, style: "normal" },
      body: { family: "Satoshi", weight: 400, style: "normal" },
      accent: { family: "JetBrains Mono", weight: 500, style: "normal" },
    };
  } else {
    for (const [role, spec] of Object.entries(decisions.fonts)) {
      if (spec && typeof spec === "object" && BANNED_FONTS.has(spec.family)) {
        console.warn(`Banned font ${spec.family} in ${role}, replacing`);
        spec.family = role === "body" ? "Satoshi" : "Clash Display";
      }
    }
  }

  // Validate colors
  if (!decisions.colors || typeof decisions.colors !== "object") {
    decisions.colors = {
      primary: "#1e1e1e",
      secondary: "#f2f2f2",
      accent: "#DB4A2B",
      background: "#ffffff",
      text: "#1e1e1e",
      muted: "#7a7a7a",
    };
  }

  // Validate sections
  if (!Array.isArray(decisions.sections) || decisions.sections.length === 0) {
    decisions.sections = [
      { type: "hero", name: "Hero", layout: "centered", notes: "" },
      { type: "features", name: "Features", layout: "grid", notes: "" },
      { type: "social_proof", name: "Social Proof", layout: "cards", notes: "" },
      { type: "cta", name: "Call to Action", layout: "centered", notes: "" },
    ];
  }

  // Validate animations
  if (!decisions.animations || typeof decisions.animations !== "object") {
    decisions.animations = {
      style: "smooth",
      easing: "cubic-bezier(0.16, 1, 0.3, 1)",
      duration: "800ms",
      scroll_reveal: true,
    };
  }

  // Validate special_components
  if (!Array.isArray(decisions.special_components)) {
    decisions.special_components = [];
  }

  return decisions as DesignDecisions;
}

function validateCopy(
  copyData: Partial<SectionCopy>,
  businessData: ResearchData
): SectionCopy {
  const name = businessData.business_name ?? "Our Business";

  if (!copyData.headline) {
    copyData.headline = `Welcome to ${name}`;
  }
  if (!copyData.subheadline) {
    copyData.subheadline =
      businessData.value_proposition ?? "Discover what we offer.";
  }
  if (!copyData.cta_primary) {
    copyData.cta_primary = { text: "Get Started", action: "#signup" };
  }
  if (!copyData.cta_secondary) {
    copyData.cta_secondary = { text: "Learn More", action: "#features" };
  }
  if (!Array.isArray(copyData.sections)) {
    copyData.sections = [];
  }
  if (!copyData.social_proof) {
    copyData.social_proof = {
      headline: "Trusted by many",
      testimonials: [],
      stats: [],
    };
  }
  if (!copyData.footer) {
    copyData.footer = { tagline: name, cta: "Get in touch" };
  }
  if (!copyData.meta) {
    copyData.meta = {
      page_title: `${name} — Official Website`,
      meta_description: (
        businessData.value_proposition ?? `Discover ${name}`
      ).slice(0, 160),
      og_title: name,
      og_description: (
        businessData.value_proposition ?? `Discover ${name}`
      ).slice(0, 100),
    };
  }

  return copyData as SectionCopy;
}

// ─── Fallback Functions ───────────────────────────────────────────────────────

function fallbackDesign(): DesignDecisions {
  return {
    selected_design_id: "DESIGN_06",
    design_name: "Clean SaaS Default",
    fonts: {
      heading: { family: "Clash Display", weight: 700, style: "normal" },
      body: { family: "Satoshi", weight: 400, style: "normal" },
      accent: { family: "JetBrains Mono", weight: 500, style: "normal" },
    },
    colors: {
      primary: "#171e19",
      secondary: "#f8f9fa",
      accent: "#ffe17c",
      background: "#ffffff",
      text: "#171e19",
      muted: "#6b7280",
    },
    ui_style: "minimal",
    color_mode: "light",
    sections: [
      {
        type: "hero",
        name: "Hero",
        layout: "centered",
        notes: "Full viewport centered headline",
      },
      {
        type: "social_proof",
        name: "Trusted By",
        layout: "logo-grid",
        notes: "Logo bar",
      },
      {
        type: "features",
        name: "Features",
        layout: "grid",
        notes: "3-column feature grid",
      },
      {
        type: "how_it_works",
        name: "How It Works",
        layout: "steps",
        notes: "3-step process",
      },
      {
        type: "testimonials",
        name: "Testimonials",
        layout: "cards",
        notes: "Review cards",
      },
      {
        type: "cta",
        name: "Get Started",
        layout: "centered",
        notes: "Final conversion section",
      },
    ],
    imagery_style: "clean photography with subtle hover effects",
    copy_tone: "clear-confident",
    animations: {
      style: "smooth",
      easing: "cubic-bezier(0.16, 1, 0.3, 1)",
      duration: "800ms",
      scroll_reveal: true,
    },
    special_components: ["highlight-bar", "gradient-cta"],
    rationale:
      "Fallback design — LLM was unable to make a selection. Using clean SaaS default.",
    _fallback: true,
  };
}

function fallbackCopy(businessData: ResearchData): SectionCopy {
  const name = businessData.business_name ?? "Our Business";
  return {
    headline: `Welcome to ${name}`,
    subheadline:
      businessData.value_proposition ?? "Discover what makes us different.",
    cta_primary: { text: "Get Started", action: "#signup" },
    cta_secondary: { text: "Learn More", action: "#features" },
    sections: [],
    social_proof: {
      headline: "Trusted by our customers",
      testimonials: [],
      stats: [],
    },
    footer: { tagline: name, cta: "Get in touch" },
    meta: {
      page_title: `${name} — Official Website`,
      meta_description: `Discover ${name} — ${businessData.value_proposition ?? "your trusted partner"}.`.slice(
        0,
        160
      ),
      og_title: name,
      og_description: `Discover ${name}`.slice(0, 100),
    },
    _fallback: true,
  };
}

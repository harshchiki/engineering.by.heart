#!/usr/bin/env python3
"""Build 20 General Tech slides and three deterministic companion GIFs.

Run with python3 build.py. Requires Chrome, Node with WebSocket, and FFmpeg.
All illustrations are original offline SVG; no Context.dev account is needed.
"""
import html
import json
from pathlib import Path
import subprocess
import tempfile

OUT = Path(__file__).resolve().parent
TOTAL = 20
REVIEWED = "2026-10-12"
C = dict(cyan="#4dd8e6", green="#36d399", red="#ff4d5e",
         orange="#ff9a3d", yellow="#ffd166", purple="#b592ff",
         blue="#5aa9ff", muted="#9aa7c7")
SOURCES = {
    "home": "https://www.context.dev/",
    "intro": "https://docs.context.dev/introduction",
    "quickstart": "https://docs.context.dev/quickstart",
    "scrape": "https://docs.context.dev/api-reference/web-scraping/scrape",
    "crawl": "https://docs.context.dev/crawl/overview",
    "answers": "https://docs.context.dev/answers/overview",
    "cache": "https://docs.context.dev/scrape/freshness-and-caching",
    "monitors": "https://docs.context.dev/monitors/overview",
    "mcp": "https://docs.context.dev/install-mcp",
    "pricing": "https://www.context.dev/pricing",
    "trust": "https://docs.context.dev/optimization/trust",
    "zdr": "https://docs.context.dev/optimization/zero-data-retention",
    "firecrawl": "https://www.firecrawl.dev/",
    "crawl4ai": "https://docs.crawl4ai.com/",
    "apify": "https://apify.com/",
    "tavily": "https://docs.tavily.com/documentation/api-reference/introduction",
    "exa": "https://exa.ai/docs",
}

STYLE = """
<meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px}
body{padding:74px 72px 70px;color:#eaf0ff;font-family:"Helvetica Neue",Arial,sans-serif;display:flex;flex-direction:column;background:radial-gradient(1200px 700px at 15% -10%,#1a2b4d,transparent 60%),radial-gradient(1000px 800px at 110% 10%,#241433,transparent 55%),linear-gradient(160deg,#0a0e1c,#0d1428 55%,#0a1020)}
.kicker{display:flex;align-items:center;gap:14px;color:#ff4d5e;font-size:26px;font-weight:800;letter-spacing:3px;text-transform:uppercase}
.dot{width:14px;height:14px;border-radius:50%;background:#ff4d5e;box-shadow:0 0 18px #ff4d5e}
h1{font-size:76px;font-weight:900;letter-spacing:-1px;line-height:1.02;margin-top:24px}
h1 span{color:#ff9a3d}.sub{font-size:31px;line-height:1.35;color:#9aa7c7;margin-top:22px}
.diagram{width:936px;height:460px;display:block;margin-top:24px;flex-shrink:0}
svg text{font-family:"Helvetica Neue",Arial,sans-serif;font-size:27px;fill:#eaf0ff;font-weight:600}
.notes{margin-top:12px;font-size:29px;line-height:1.3;color:#cdd7f2}
.notes p+p{margin-top:12px}.notes b{color:#eaf0ff}
.analogy{margin-top:22px;padding:22px 28px;border:1px solid #2b3658;border-left:7px solid #ff9a3d;border-radius:20px;font-size:30px;line-height:1.35;background:#ff9a3d12}
.analogy b{color:#ff9a3d}.source{font-size:24px;color:#9aa7c7;margin-top:14px;line-height:1.3}
.spacer{flex:1}.footer{margin-top:28px;padding-top:24px;border-top:1px solid #2b3658;display:flex;justify-content:space-between;font-size:24px;font-weight:600;color:#9aa7c7;flex-shrink:0}
.brand{color:#eaf0ff;font-weight:800}.page{color:#ff4d5e}.swipe{color:#ff9a3d}
.code{padding:26px 28px;border:1px solid #2b3658;border-radius:22px;background:#161d33;margin-top:28px;white-space:pre-wrap;font:25px/1.55 Menlo,monospace;color:#4dd8e6}
.smallscene{height:190px}.recap{margin-top:28px;display:grid;gap:14px}
.rule{padding:11px 26px;border:1px solid #2b3658;border-left:6px solid #36d399;border-radius:16px;font-size:30px;line-height:1.3;background:#161d33}
.resources{font-size:25px;line-height:1.5;margin-top:25px;color:#9aa7c7}.resources a{color:#4dd8e6;text-decoration:none}
</style>
"""


def text(x, y, lines, color=None, size=27, anchor="middle", id=None):
    size += 5
    lines = [lines] if isinstance(lines, str) else lines
    attrs = f' id="{id}"' if id else ""
    fill = f' style="fill:{C.get(color, color)}"' if color else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}"{fill}{attrs}>' + "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else size + 9}" style="font-size:{size}px">{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)) + "</text>"


def box(x, y, w, h, title, detail="", color="cyan", db=False):
    c = C[color]
    shape = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#161d33" stroke="{c}" stroke-width="2"/>'
    if db:
        shape = f'<path d="M{x} {y+20} V{y+h-20} C{x} {y+h+6},{x+w} {y+h+6},{x+w} {y+h-20} V{y+20}" fill="#161d33" stroke="{c}" stroke-width="2"/><ellipse cx="{x+w/2}" cy="{y+20}" rx="{w/2}" ry="20" fill="#1c2440" stroke="{c}" stroke-width="2"/>'
    return f'<g data-node="{html.escape(title)}" data-x="{x}" data-y="{y}" data-w="{w}" data-h="{h}">' + shape + text(x+w/2, y+h/2-3 if detail else y+h/2+9, title, color) + (
        text(x+w/2, y+h/2+34, detail, "muted", 24) if detail else "") + '</g>'


def arrow(points, label="", color="cyan", lx=None, ly=None, dashed=False):
    pts = " ".join(f"{x},{y}" for x, y in points)
    dash = ' stroke-dasharray="10 8"' if dashed else ""
    result = f'<polyline points="{pts}" fill="none" stroke="{C[color]}" stroke-width="4" marker-end="url(#{color})"{dash}/>'
    if label:
        result += text(lx if lx is not None else (points[0][0]+points[-1][0])/2,
                       ly if ly is not None else (points[0][1]+points[-1][1])/2-18,
                       label, color, 24)
    return result


def svg(contents, paths=None, dynamic="", small=False):
    defs = "".join(f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10Z" fill="{v}"/></marker>' for k, v in C.items())
    tokens = "".join(f'<circle id="token{i}" r="11" fill="#ffd166" stroke="#0a1020" stroke-width="3" visibility="hidden"/>' for i, _ in enumerate(paths or []))
    height = 190 if small else 540
    cls = "diagram smallscene" if small else "diagram"
    return dict(scene=f'<svg class="{cls}" viewBox="0 0 936 {height}" role="img"><defs>{defs}</defs>{contents}{tokens}</svg>',
                paths=paths or [], dynamic=dynamic)


def rows(items):
    result = ""
    for i, (left, center, right, color) in enumerate(items):
        y = 28 + i*126
        result += f'<rect x="5" y="{y}" width="926" height="107" rx="18" fill="#161d33" stroke="#2b3658"/><rect x="5" y="{y}" width="6" height="107" rx="3" fill="{C[color]}"/>'
        result += '<g data-cell-end="292">' + text(32, y+38, left, color, 27, "start") + '</g>'
        result += '<g data-cell-end="630">' + text(310, y+38, center, size=25, anchor="start") + '</g>'
        result += '<g data-cell-end="918">' + text(650, y+38, right, "muted", 25, "start") + '</g>'
    return result


SLIDES = []


def add(title, subtitle, scene, notes, concepts, refs, source_label, motion="", analogy="", code=""):
    # Storyboard: number, source concepts, visible scene, static/GIF choice, causal motion.
    SLIDES.append(dict(number=len(SLIDES)+1, title=title, subtitle=subtitle,
                       notes=notes, concepts=concepts, refs=refs, source_label=source_label,
                       motion=motion, analogy=analogy, code=code, **scene))


add('Your AI needs<br><span>better context.</span>',
    "Context.dev: what it does, where it fits, and when to choose something else.",
    svg(box(18, 35, 230, 130, "Messy web", "pages + files", "blue") +
        arrow([(248, 100), (345, 100)], "fetch", lx=295, ly=80) +
        box(345, 20, 245, 160, "Context.dev", "web data API", "orange") +
        arrow([(590, 100), (688, 100)], "deliver", lx=640, ly=80) +
        box(688, 35, 230, 130, "Your AI app", "reads the data", "green"), small=True),
    "<p><b>The payoff:</b> spend less effort operating scraping infrastructure.</p>",
    "Product definition, evaluation scope, live web context is an input not truth.",
    ["home", "intro"], "Source: context.dev + product documentation",
    analogy="Like a <b>research assistant</b> who collects documents. Your application still decides what to trust.")

add('A web API.<br>Not <span>AI memory.</span>',
    "It supplies outside information; it does not replace your model or application.",
    svg(box(45, 45, 375, 135, "Context.dev", "hosted web data", "cyan") +
        box(510, 45, 375, 135, "Context7", "different product", "purple") +
        box(45, 275, 375, 135, "LLM / memory", "still your responsibility", "orange") +
        box(510, 275, 375, 135, "Vector database", "still your responsibility", "green") +
        text(468, 235, "Similar names do not mean similar jobs.", "yellow", 29) +
        text(468, 492, "No self-hosted Context.dev edition advertised.", "muted", 27)),
    "<p><b>Fresher tip:</b> an API is a service your software calls. A language model uses the returned data to answer.</p>",
    "Not Context7, not a model, agent memory or vector DB; hosted service boundary.",
    ["home", "intro"], "Source: context.dev; product-boundary analysis")

add('Pick the <span>right tool.</span>',
    "Start with what you already have, not with the flashiest endpoint.",
    svg(rows([
        ("Known URL", ["Scrape", "read one page"], ["Markdown, HTML", "JSON, screenshot"], "cyan"),
        ("Website", ["Map → choose URLs", "or Crawl → pages"], ["Map: links", "Crawl: page text"], "blue"),
        ("Search query", ["Search", "find relevant pages"], ["Results, with", "optional content"], "purple"),
        ("Research task", ["Answers", "research + synthesize"], ["Structured answer", "with source URLs"], "green"),
    ])),
    "<p><b>Cost discipline:</b> do not use an AI research call to read a URL you already know.</p>",
    "Scrape vs Map vs Crawl vs Search vs Answers selection.",
    ["intro", "answers"], "Source: docs.context.dev · API overview")

add('One key.<br><span>Broader context.</span>',
    "The same platform also covers company data, files and change detection.",
    svg(box(338, 195, 260, 120, "Same API key", "many data jobs", "orange") +
        box(20, 30, 360, 120, "Brand + Styleguide", "logos + design tokens", "cyan") +
        box(555, 30, 360, 120, "People + News", "profiles + news", "purple") +
        box(20, 380, 360, 120, "Parse", "files → Markdown", "blue") +
        box(555, 380, 360, 120, "Monitors", "pages, URLs, key values", "green") +
        arrow([(380, 120), (420, 195)], color="cyan") +
        arrow([(555, 120), (520, 195)], color="purple") +
        arrow([(380, 415), (420, 315)], color="blue") +
        arrow([(555, 415), (520, 315)], color="green")),
    "<p><b>Useful fit:</b> branded onboarding, company research and public-document ingestion.</p><p><b>Not automatic truth:</b> verify identity matches, freshness and rights to reuse assets.</p>",
    "Brand and styleguide, people identity checks, news, uploaded file parsing, monitors and branding rights.",
    ["home", "intro"], "Source: context.dev · API catalog")

add('Start with<br><span>one request.</span>',
    "Server-side REST works without an SDK. Keep the secret out of browser code.",
    svg(box(20, 45, 230, 100, "Your server", "env secret", "blue") +
        arrow([(250, 95), (357, 95)], "POST", lx=304, ly=76) +
        box(357, 45, 250, 100, "Scrape API", "Context.dev", "orange") +
        arrow([(607, 95), (709, 95)], "JSON", lx=658, ly=76) +
        box(709, 45, 210, 100, "Your code", "validate", "green"), small=True),
    "<p><b>Read:</b> <code>markdown.data</code> only after <code>markdown.success</code> is true.</p><p><b>Agent route:</b> MCP uses OAuth at <code>mcp.context.dev/mcp</code>; SDKs serve application code.</p>",
    "Exact REST body, Authorization header secret, Markdown data/success, server-only key, SDK and OAuth MCP.",
    ["quickstart", "mcp", "scrape"], "Source: Quickstart + MCP guide",
    code='curl https://api.context.dev/v1/web/scrape \\\n  -H "Authorization: $CONTEXT_DEV_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d \'{\n    "url": "https://example.com",\n    "formats": { "markdown": true },\n    "maxAgeMs": 0\n  }\'')

add('HTTP 200 is<br>not <span>all-success.</span>',
    "One response can succeed for Markdown and fail for a screenshot.",
    svg(box(270, 30, 395, 100, "HTTP 200", "inspect individual outputs", "yellow") +
        arrow([(390, 130), (260, 225)], color="green") +
        arrow([(550, 130), (690, 225)], color="red") +
        box(30, 225, 410, 135, "markdown.success: true", "usable text", "green") +
        box(500, 225, 410, 135, "screenshot: failed", "error_code + message", "red") +
        text(468, 425, ["Never convert a missing output", "into a success-shaped empty value."], "yellow", 30)),
    "<p><b>Validate:</b> requested output, success flag, content and your own field types.</p><p><b>Investigate:</b> record <code>request_id</code>; retry only the failure you actually need.</p>",
    "Partial success, all output keys, unrequested success=null, per-output validation, request IDs.",
    ["scrape", "quickstart"], "Source: Scrape response contract")

s = box(22, 35, 260, 110, "1 Public docs", "approved URLs", "blue")
s += box(337, 35, 260, 110, "2 Crawl", "limit scope", "cyan")
s += box(652, 35, 260, 110, "3 Chunk", "small passages", "purple")
s += box(652, 285, 260, 120, "4 Your index", "searchable text", "purple", True)
s += box(337, 285, 260, 120, "5 Retrieve", "matched text", "green")
s += box(22, 285, 260, 120, "6 LLM answer", "cite source URLs", "green")
ragpath = [(282, 90), (337, 90), (597, 90), (652, 90), (782, 145), (782, 285), (652, 345), (597, 345), (337, 345), (282, 345), (22, 345)]
s += arrow([(282, 90), (337, 90)]) + arrow([(597, 90), (652, 90)])
s += arrow([(782, 145), (782, 285)], "store", lx=828, ly=227, color="purple")
s += arrow([(652, 345), (597, 345)], color="green") + arrow([(337, 345), (282, 345)], color="green")
s += text(468, 492, "RAG = retrieve evidence before generating an answer.", "cyan", 27)
add('Build <span>grounded answers.</span>', "Example: a support bot over public product documentation.",
    svg(s, [ragpath]),
    "<p><b>Your pipeline owns:</b> cleanup, deduplication, indexing, access rules and citations.</p><p><b>Keep provenance:</b> URL + capture time + content version; refresh changed pages.</p>",
    "RAG ingestion architecture, public docs use case, embeddings/index optional app-owned, provenance and updates.",
    ["crawl", "cache", "intro"], "Source: Crawl docs; recommended RAG architecture",
    motion="One document travels through capture, chunking, indexing and retrieval. Illustrative sequence, not latency.")

add('Extract fields.<br><span>Choose the method.</span>',
    "Known page structure and open-ended meaning are different problems.",
    svg(box(20, 50, 420, 130, "CSS rules", "known selectors", "cyan") +
        box(496, 50, 420, 130, "AI JSON extraction", "JSON Schema", "purple") +
        arrow([(230, 180), (230, 295)], "parseParams.rules", lx=230, ly=242) +
        arrow([(706, 180), (706, 295)], "jsonParams.schema", "purple", lx=706, ly=242) +
        box(20, 295, 420, 125, "h1 → title", "selectors can break", "cyan") +
        box(496, 295, 420, 125, "text → typed fields", "models can infer wrongly", "purple") +
        text(468, 500, "Both need validation against the source.", "yellow", 30)),
    "<p><b>Product catalogs:</b> check price, currency, availability and locale; never guess a missing price.</p><p><b>Prefer deterministic rules</b> when the page structure is stable.</p>",
    "Deterministic CSS parse vs schema-based AI JSON, product extraction use case, field validation.",
    ["scrape", "pricing"], "Source: Scrape reference + credit costs")

add('Research is<br>not <span>verification.</span>',
    "Answers returns a JSON-shaped synthesis plus source URLs.",
    svg(box(30, 40, 270, 115, "Task + example", "json_format", "blue") +
        arrow([(300, 98), (378, 98)]) +
        box(378, 40, 230, 115, "Answers", "web research", "orange") +
        arrow([(608, 98), (686, 98)]) +
        box(686, 40, 220, 115, "Cited JSON", "json_content", "green") +
        box(30, 280, 390, 130, "Fast: 10 credits", "speed-first lookup", "cyan") +
        box(516, 280, 390, 130, "Ultra: 100 credits", "default; deeper research", "purple") +
        text(468, 220, "Example shape ≠ JSON Schema", "yellow", 32) +
        text(468, 495, "Open the cited pages before trusting key claims.", "green", 28)),
    "<p><b>Useful for:</b> vendor comparisons, company summaries and research assistants.</p><p><b>Handle uncertainty:</b> check sources and partial results; citations alone do not prove a claim.</p>",
    "Answers task and example object vs Scrape JSON Schema, fast vs default ultra, sources and partial outputs.",
    ["answers", "pricing"], "Source: Answers guide + current pricing")

add('Use it where<br><span>web data matters.</span>',
    "Treat it as a collection layer inside a larger product.",
    svg(box(25, 30, 400, 155, "Public knowledge bot", "docs → evidence", "cyan") +
        box(505, 30, 400, 155, "Company onboarding", "domain → logo + colors", "blue") +
        box(25, 290, 400, 155, "Market intelligence", "research → cited briefs", "purple") +
        box(505, 290, 400, 155, "Catalog / change feed", "pages → validated updates", "green") +
        arrow([(225, 185), (225, 290)], "same collection layer", lx=468, ly=246, dashed=True) +
        text(468, 510, "Customer value comes from your app, not the scrape.", "orange", 28)),
    "<p><b>Strongest fit:</b> several web-data jobs, one managed integration, little crawler infrastructure to maintain.</p>",
    "Practical use cases and integrated-platform advantage; decision judgment not benchmark.",
    ["home", "intro", "monitors"], "Source: product catalog; use-case assessment")

s = box(25, 50, 260, 125, "1 Baseline", "no first alert", "blue")
s += box(337, 50, 260, 125, "2 Recheck", "compare text", "cyan")
s += box(649, 50, 260, 125, "3 Change event", "signed webhook", "green")
s += arrow([(285, 113), (337, 113)]) + arrow([(597, 113), (649, 113)], color="green")
s += box(50, 285, 375, 135, "Exact detection", "any text difference", "cyan")
s += box(505, 285, 375, 135, "Semantic detection", "AI judges what matters", "purple")
s += text(468, 480, "ILLUSTRATIVE CHECK: a pricing page changes.", "muted", 24)
s += text(468, 524, "Baseline saved → new text found → event received", "yellow", 27, id="monitorState")
dynamic = """
document.getElementById('monitorState').textContent =
 t < 1.1 ? '1 Baseline saved; no change alert' :
 t < 2.7 ? '2 Later check finds new page text' :
 t < 4.8 ? '3 Signed event reaches your receiver' :
 t < 5.5 ? 'Verify signature; deduplicate event' : 'Reset: establish the first baseline';
"""
add('Watch for<br><span>meaningful changes.</span>',
    "Example: public changelogs, pricing pages or sitemap additions.",
    svg(s, [[(285, 113), (337, 113), (597, 113), (649, 113), (909, 113)]], dynamic),
    "<p><b>Receiver:</b> verify signatures and deduplicate by <code>X-Context-Id</code>.</p><p><b>No alert ≠ no change:</b> failed runs send no webhook. Check run health; default schedule is daily.</p>",
    "Baseline no alert, schedules, exact/semantic distinction, signed webhooks deduplication, failure heartbeat.",
    ["monitors"], "Source: Monitors guide · compressed illustrative time",
    motion="Baseline is established, a later check finds a change, then a signed event is delivered; visible outcome hold.")

s = box(20, 70, 270, 130, "Default scrape", "up to 3 days", "yellow")
s += box(350, 70, 235, 130, "Cached text", "may be older", "yellow")
s += arrow([(290, 135), (350, 135)], color="yellow")
s += box(20, 305, 270, 130, "maxAgeMs: 0", "fresh capture", "green")
s += box(350, 305, 235, 130, "Live fetch", "new page visit", "green")
s += arrow([(290, 370), (350, 370)], color="green")
s += box(682, 180, 230, 135, "Your app", "check age", "blue")
s += arrow([(585, 135), (633, 135), (633, 227), (682, 227)], color="yellow")
s += arrow([(585, 370), (633, 370), (633, 273), (682, 273)], color="green")
s += text(468, 512, "Fresh fetch ≠ proof that the source is accurate.", "orange", 29, id="cacheState")
dynamic = """
document.getElementById('cacheState').textContent =
 t < 2.75 ? 'Default path can return older captured content.' :
 t < 5.5 ? 'maxAgeMs: 0 requests a fresh page capture.' :
 'Reset: compare cached and fresh requests.';
"""
add('“Live” can<br>mean <span>cached.</span>',
    "Freshness is a policy you must choose, not a promise you should assume.",
    svg(s, [[(290, 135), (350, 135), (585, 135), (633, 135), (633, 227), (682, 227)],
            [(290, 370), (350, 370), (585, 370), (633, 370), (633, 273), (682, 273)]], dynamic),
    "<p><b>Read the age:</b> <code>cache_metadata.age_ms</code> reports the oldest contributing cached data.</p><p><b>Independent caches:</b> outputs can come from different visits. Request them together with <code>maxAgeMs: 0</code> when they must align.</p>",
    "Three-day default, maxAgeMs0, age metadata, independent output caches and same-visit request.",
    ["cache"], "Source: Freshness and caching guide",
    motion="Two sequential requests compare a default cache path with an explicit fresh-fetch path.")

add('Budget <span>credits.</span><br>Not just requests.',
    "Pricing snapshot: 12 Oct 2026. Recheck before buying.",
    svg(rows([
        ("Standard scrape", ["1 credit base", "2 with actions"], ["JS + proxies", "included"], "cyan"),
        ("AI JSON", ["Base + 4 credits", "when JSON succeeds"], ["Usually 5 total", "without actions"], "purple"),
        ("Free plan", ["$0 / month", "1,000 credits"], ["1 concurrent call", "no overage"], "blue"),
        ("Paid examples", ["$19 / 7,500 credits", "$99 / 125,000 credits"], ["Developer / Pro", "monthly prices"], "green"),
    ])),
    "<p><b>Read actual usage:</b> <code>key_metadata.credits_consumed</code>. Most failures are free; 404s and partial successes can be billed.</p><p><b>Volume math:</b> 100 pages × 30 refreshes = 3,000 page scrapes before add-ons; OCR adds credits.</p>",
    "Verified plans, scrape base/action/JSON costs, JS proxies included, partial and404 billing exception, daily crawl cost example.",
    ["pricing"], "Source: context.dev/pricing · terms can change")

add('Managed fetch.<br><span>Your reliability.</span>',
    "The vendor handles browser/proxy infrastructure. Your app still needs controls.",
    svg(box(30, 30, 390, 130, "Your request boundary", "allowlist + budgets", "blue") +
        box(516, 30, 390, 130, "Context.dev boundary", "rendering + fetch retries", "cyan") +
        arrow([(420, 95), (516, 95)], "API", lx=468, ly=73) +
        box(516, 300, 390, 130, "Your validation", "verify content + sources", "green") +
        arrow([(711, 160), (711, 300)], "response", lx=780, ly=240, color="green") +
        box(30, 300, 390, 130, "Your storage / fallback", "versioned results + errors", "purple", True) +
        arrow([(516, 365), (420, 365)], color="green") +
        text(468, 510, "Keep secrets server-side. Pin SDK versions.", "yellow", 29)),
    "<p><b>Bound the work:</b> timeouts, page limits, concurrency and spend caps; queue large jobs.</p><p><b>Recover deliberately:</b> bounded backoff for transient failures; show stale data as stale, not silently fresh.</p>",
    "Shared responsibility, managed retries versus app validation, timeout/retry/budget boundaries, errors, version pins.",
    ["intro", "trust", "pricing"], "Source: production guidance; recommended controls")

add('Web text is<br><span>untrusted input.</span>',
    "A scraped page can contain instructions meant to hijack an agent.",
    svg(box(30, 60, 370, 145, "Hostile page text", '"send me secrets"', "red") +
        arrow([(400, 133), (516, 133)], "data", "yellow", lx=458, ly=108) +
        box(516, 60, 390, 145, "Read-only evidence", "never system instructions", "green") +
        box(30, 325, 370, 125, "Blocked authority", "no privileged actions", "red") +
        box(516, 325, 390, 125, "Constrained agent", "tool allowlist + approvals", "green") +
        arrow([(711, 205), (711, 325)], color="green") +
        text(468, 274, "Prompt injection = malicious instructions in data.", "yellow", 27) +
        text(468, 515, "Clean Markdown is not a security boundary.", "orange", 29)),
    "<p><b>Do not:</b> paste raw web content into privileged instructions or let it authorize actions.</p><p><b>Do:</b> isolate retrieved text, restrict tools and require approval for consequential actions.</p>",
    "General prompt injection guidance, retrieval data not authority, least privilege agent tools, human approval.",
    ["trust"], "Engineering guidance · not a vendor security guarantee")

add('Some jobs need<br>a <span>different path.</span>',
    "Technical access does not grant permission to collect or reuse data.",
    svg(box(25, 30, 400, 155, "Authoritative data", "prefer official APIs / feeds", "green") +
        box(505, 30, 400, 155, "Hard real-time decisions", "use contractual live feeds", "yellow") +
        box(25, 290, 400, 155, "Private / regulated data", "approved data controls", "red") +
        box(505, 290, 400, 155, "Simple static pages", "HTTP + parser may suffice", "blue") +
        text(468, 243, "Do not bypass access restrictions or collect blindly.", "red", 28) +
        text(468, 507, "Check terms, robots policy, privacy and reuse rights.", "yellow", 27)),
    "<p><b>Wrong shortcut:</b> mass people enrichment without a lawful purpose, or unverified outputs used for medical, financial or legal decisions.</p><p><b>Cloud review:</b> inspect retention, DPA and subprocessors before sending sensitive content.</p>",
    "Non-use cases official API/source of truth realtime sensitive/simple, privacy permissions terms robots copyright rights high-stakes.",
    ["trust", "zdr"], "Source: data-control docs; suitability guidance")

add('Watch the<br><span>sharp edges.</span>',
    "Documented limits and source behavior matter more than the homepage promise.",
    svg(rows([
        ("Crawl scope", ["Up to 500 pages", "in one Crawl call"], ["Use Batches", "for larger jobs"], "cyan"),
        ("Brand freshness", ["Cache default", "about 90 days"], ["Set maxAgeMs: 0", "for fresh retrieval"], "yellow"),
        ("Page variability", ["Country, login,", "locale, dynamic UI"], ["Test page variants", "across locales"], "purple"),
        ("Zero retention", ["Enable entitlement;", "request + confirm"], ["No Batches or", "Monitors mode"], "red"),
    ])),
    "<p><b>ZDR is not universal:</b> Brand retrieval also lacks this mode; it skips PDF OCR where supported.</p><p><b>Not “scrape anything”:</b> no blanket guarantee for every blocked site, login flow or missing field.</p>",
    "Crawl500 batches, brand90d, geo/locale/page variation, ZDR entitlement/header limitations batch monitor brand OCR.",
    ["crawl", "pricing", "zdr"], "Source: Crawl + pricing + zero-retention docs")

add('Alternatives for<br><span>web ingestion.</span>',
    "These are candidates for different constraints, not a performance ranking.",
    svg(rows([
        ("Firecrawl", ["Managed scraping", "open-source option"], ["Self-host ≠ full", "hosted capability"], "orange"),
        ("Crawl4AI", ["Python crawler", "custom extraction"], ["You run browsers,", "proxies and ops"], "green"),
        ("Apify", ["Ready-made Actors", "for site-specific jobs"], ["Check quality", "and pricing"], "purple"),
        ("Build directly", ["HTTP / Scrapy", "or Playwright"], ["Maximum control;", "your maintenance"], "blue"),
    ])),
    "<p><b>Context.dev advantage:</b> one hosted key for web data plus brand, people, news and monitoring.</p><p><b>Better for you?</b> local control, a specialized scraper or a simpler fetch can outweigh that breadth.</p>",
    "Alternative ingestion tools, managed and open-source distinctions, self-host gaps, Apify third-party actors, DIY ops tradeoff.",
    ["firecrawl", "crawl4ai", "apify", "home"], "Sources: firecrawl.dev · docs.crawl4ai.com · apify.com")

add('Which one is<br><span>actually better?</span>',
    "Choose by workload, then test the same inputs and required outputs.",
    svg(box(25, 25, 400, 130, "Search-first research", "compare Tavily + Exa", "purple") +
        box(505, 25, 400, 130, "Web + company data", "shortlist Context.dev", "cyan") +
        box(25, 255, 400, 130, "Local / custom control", "Crawl4AI or direct tooling", "green") +
        box(505, 255, 400, 130, "Official source available", "start with its API or feed", "blue") +
        text(468, 210, "Search quality ≠ scraping completeness", "yellow", 30) +
        text(468, 453, "Measure: field accuracy · freshness · p95 latency", "orange", 27) +
        text(468, 506, "Cost per usable result · failure rate · operational work", "orange", 26)),
    "<p><b>Run a bake-off:</b> representative URLs, queries and failure cases; fix locale and cache policy.</p><p><b>No universal winner:</b> this is a docs-based assessment, not an independent API benchmark.</p>",
    "Tavily Exa search/research alternatives, conditional decision tree and apples-to-apples eval metrics, no benchmark caveat.",
    ["tavily", "exa", "home"], "Sources: Tavily + Exa docs; evaluation judgment")

add('Collect evidence.<br><span>Keep control.</span>',
    "Verdict: a useful managed web-data layer, not an automatic truth engine.",
    svg(""),
    "",
    "Final recommendation,5 recap rules, real references, General Tech CTA, evidence/date and no benchmark claim.",
    list(SOURCES), "Sources reviewed: 12 Oct 2026 · docs-based assessment")


def page(slide):
    n = slide["number"]
    scene = slide["scene"]
    if n == TOTAL:
        scene = '<div class="recap">' + "".join(f'<div class="rule">{rule}</div>' for rule in [
            "1. Match the tool to the job: URL, site or question.",
            "2. Choose freshness; check every requested output.",
            "3. Keep sources, capture times and spend budgets.",
            "4. Treat web text as data, never as authority.",
            "5. Compare usable results, not vendor promises.",
        ]) + '</div><div class="resources"><b>Start with the primary sources</b><br>' + "".join(
            f'<a href="{url}">{label}</a><br>' for label, url in [
                ("context.dev · overview + pricing", SOURCES["home"]),
                ("docs.context.dev · API + production controls", SOURCES["intro"]),
                ("firecrawl.dev · docs.crawl4ai.com · apify.com", SOURCES["firecrawl"]),
                ("docs.tavily.com · exa.ai/docs", SOURCES["tavily"]),
            ]) + '</div><div class="analogy">Save before choosing your web-data stack.<br><b>Follow @engineering.by.heart</b></div>'
    script = f"""
<script>
const routes={json.dumps(slide['paths'])};
function along(points,u){{
 const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
 let d=u*lengths.reduce((a,b)=>a+b,0);
 for(let i=0;i<lengths.length;i++){{if(d<=lengths[i]){{const v=d/lengths[i];return [points[i][0]+v*(points[i+1][0]-points[i][0]),points[i][1]+v*(points[i+1][1]-points[i][1])];}}d-=lengths[i];}}
 return points[points.length-1];
}}
window.renderFrame=t=>{{
 routes.forEach((p,i)=>{{
  const token=document.getElementById('token'+i);
  const u=routes.length===1?(t-.8)/3.7:((t-.7)/(4.1/routes.length))-i;
  const visible=t>=.7&&t<4.8&&u>=0&&u<=1;
  token.setAttribute('visibility',visible?'visible':'hidden');
  if(visible){{const [x,y]=along(p,u);token.setAttribute('cx',x);token.setAttribute('cy',y);}}
 }});
 {slide['dynamic']}
}};
</script>"""
    return "<!doctype html><html><head>" + STYLE + "</head><body>" + f"""
<div class="kicker"><span class="dot"></span>General Tech · Context.dev</div>
<h1>{slide['title']}</h1><div class="sub">{slide['subtitle']}</div>
{scene}
{f'<pre class="code">{html.escape(slide["code"])}</pre>' if slide['code'] else ''}
{f'<div class="analogy">{slide["analogy"]}</div>' if slide['analogy'] else ''}
{f'<div class="notes">{slide["notes"]}</div>' if slide['notes'] else ''}
<div class="source">{slide['source_label']}</div>
<div class="spacer"></div>
<div class="footer"><div><span class="brand">@engineering.by.heart</span> · General Tech</div><div><span class="page">{n:02d}/{TOTAL:02d}</span> &nbsp; <span class="swipe">{"SAVE" if n == TOTAL else "SWIPE →"}</span></div></div>
""" + script + "</body></html>"


def main():
    assert len(SLIDES) == TOTAL and 2 <= TOTAL <= 20
    expected = {f"{n}.png" for n in range(1, TOTAL+1)} | {
        f'{s["number"]}.gif' for s in SLIDES if s["motion"]}
    stale = [p.name for p in OUT.iterdir() if p.suffix.lower() in {".png", ".gif", ".jpg", ".jpeg", ".webp"} and p.name not in expected]
    if stale:
        raise ValueError(f"Unexpected publishable media: {stale}")
    (OUT / "sources.json").write_text(json.dumps(dict(reviewed=REVIEWED, basis="Primary documentation; no independent API benchmark", sources=SOURCES, storyboard=[
        dict(number=s["number"], concepts=s["concepts"], refs=s["refs"], title=s["title"],
             format="PNG + GIF" if s["motion"] else "PNG", motion=s["motion"],
             scene=s["scene"]) for s in SLIDES]), indent=2) + "\n")
    with tempfile.TemporaryDirectory(prefix="context-carousel-build-") as tmp:
        work = Path(tmp)
        manifest = dict(out=str(OUT), slides=[])
        for slide in SLIDES:
            file = work / f'{slide["number"]}.html'
            file.write_text(page(slide))
            manifest["slides"].append(dict(number=slide["number"], file=str(file), animated=bool(slide["motion"])))
        (work / "manifest.json").write_text(json.dumps(manifest))
        subprocess.run(["node", str(OUT / "render.cjs"), str(work / "manifest.json")],
                       check=True, timeout=900)
    import os
    if os.environ.get("AUDIT_ONLY"):
        print("Layout audit finished; images were not rendered in audit-only mode.")
    else:
        print(f"Done: {TOTAL} PNGs + 3 GIFs in {OUT}")


if __name__ == "__main__":
    main()

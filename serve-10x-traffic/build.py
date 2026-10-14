#!/usr/bin/env python3
"""Render section 1.1.3 as 18 PNG posters and eight deterministic GIF loops.

Requires Chrome, Node.js with built-in WebSocket, and FFmpeg. No network assets.
Run: python3 build.py
"""
import html
import json
import os
from pathlib import Path
import subprocess
import tempfile

OUT = Path(__file__).resolve().parent
TOTAL = 18
COLORS = dict(cyan="#4dd8e6", green="#36d399", red="#ff4d5e",
              orange="#ff9a3d", yellow="#ffd166", purple="#b592ff",
              blue="#5aa9ff", muted="#9aa7c7")

STYLE = """
<meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px}
body{padding:74px 72px 70px;color:#eaf0ff;font-family:"Helvetica Neue",Arial,sans-serif;display:flex;flex-direction:column;background:radial-gradient(1200px 700px at 15% -10%,#1a2b4d,transparent 60%),radial-gradient(1000px 800px at 110% 10%,#241433,transparent 55%),linear-gradient(160deg,#0a0e1c,#0d1428 55%,#0a1020)}
.kicker{display:flex;align-items:center;gap:14px;color:#ff4d5e;font-size:26px;font-weight:800;letter-spacing:3px;text-transform:uppercase}
.dot{width:14px;height:14px;border-radius:50%;background:#ff4d5e;box-shadow:0 0 18px #ff4d5e}
h1{font-size:76px;font-weight:900;letter-spacing:-1px;line-height:1.02;margin-top:24px}
h1 span{color:#ff9a3d}.sub{font-size:30px;line-height:1.35;color:#9aa7c7;margin-top:22px}
.diagram{width:936px;height:580px;display:block;margin-top:24px;flex-shrink:0}
svg text{font-family:"Helvetica Neue",Arial,sans-serif;font-size:26px;fill:#eaf0ff;font-weight:600}
.notes{margin-top:18px;font-size:29px;line-height:1.4;color:#cdd7f2}
.notes p+p{margin-top:12px}.notes b{color:#eaf0ff}
.analogy{margin-top:24px;padding:26px 30px;border:1px solid #2b3658;border-left:7px solid #ff9a3d;border-radius:20px;font-size:31px;line-height:1.35;background:#ff9a3d12}
.analogy b{color:#ff9a3d}
.spacer{flex:1}.footer{margin-top:28px;padding-top:24px;border-top:1px solid #2b3658;display:flex;justify-content:space-between;font-size:25px;font-weight:600;color:#9aa7c7}
.brand{color:#eaf0ff;font-weight:800}.page{color:#ff4d5e}.swipe{color:#ff9a3d}
.recap{margin-top:26px;display:grid;gap:12px}.rule{padding:14px 26px;border:1px solid #2b3658;border-left:6px solid #36d399;border-radius:16px;font-size:30px;background:#161d33}
.resources{font-size:26px;line-height:1.6;margin-top:25px;color:#9aa7c7}.resources a{color:#4dd8e6;text-decoration:none}
.recap~.resources{line-height:1.4;margin-top:22px}.recap~.analogy{padding:20px 30px}
</style>
"""


def text(x, y, lines, color=None, size=26, anchor="middle", id=None):
    if isinstance(lines, str):
        lines = [lines]
    attrs = f' id="{id}"' if id else ""
    fill = f' style="fill:{COLORS.get(color, color)}"' if color else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}"{fill}{attrs}>' + "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else size + 8}" style="font-size:{size}px">{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)) + "</text>"


def box(x, y, w, h, title, detail="", color="cyan", db=False):
    c = COLORS[color]
    shape = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#161d33" stroke="{c}" stroke-width="2"/>'
    if db:
        shape = f'<path d="M{x} {y+20} V{y+h-20} C{x} {y+h+6},{x+w} {y+h+6},{x+w} {y+h-20} V{y+20}" fill="#161d33" stroke="{c}" stroke-width="2"/><ellipse cx="{x+w/2}" cy="{y+20}" rx="{w/2}" ry="20" fill="#1c2440" stroke="{c}" stroke-width="2"/>'
    return shape + text(x+w/2, y+h/2-3 if detail else y+h/2+9, title, color) + (text(x+w/2, y+h/2+33, detail, "muted", 24) if detail else "")


def arrow(points, label="", color="cyan", lx=None, ly=None, dashed=False, id=None):
    pts = " ".join(f"{x},{y}" for x, y in points)
    attrs = f' id="{id}"' if id else ""
    path = f'<polyline points="{pts}" fill="none" stroke="{COLORS[color]}" stroke-width="4" marker-end="url(#{color})"{" stroke-dasharray=\"10 8\"" if dashed else ""}{attrs}/>'
    if label:
        path += text(lx if lx is not None else (points[0][0]+points[-1][0])/2,
                     ly if ly is not None else (points[0][1]+points[-1][1])/2-16,
                     label, color, 24)
    return path


def svg(contents, paths=None, dynamic=""):
    defs = "".join(f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="{v}"/></marker>' for k, v in COLORS.items())
    tokens = ""
    if paths:
        for i, _ in enumerate(paths):
            tokens += f'<circle id="token{i}" r="10" fill="#ffd166" stroke="#0a1020" stroke-width="3" visibility="hidden"/>'
    return f'<svg class="diagram" viewBox="0 0 936 580" role="img" aria-label="Technical mechanism diagram"><defs>{defs}</defs>{contents}{tokens}</svg>', paths or [], dynamic


SLIDES = []


def add(title, subtitle, scene, notes, concepts, motion="", analogy=""):
    # Storyboard metadata records source coverage, visible scene, and what time teaches.
    SLIDES.append(dict(number=len(SLIDES)+1, title=title, subtitle=subtitle,
                       scene=scene[0], paths=scene[1], dynamic=scene[2], notes=notes,
                       concepts=concepts, motion=motion, analogy=analogy))


add('Serve <span>10x traffic.</span><br>Not 10x complexity.',
    "Build for more demand before demand arrives.",
    svg(box(30, 110, 240, 110, "1x demand", "one service") +
        arrow([(285, 165), (410, 165)], "grow", ly=142, color="orange") +
        box(430, 65, 230, 100, "Replica A") + box(430, 210, 230, 100, "Replica B") +
        box(430, 355, 230, 100, "Replica N") +
        text(775, 210, ["Shared state.", "Same contract.", "More capacity."], "green") +
        text(330, 540, "Measure → offload → scale → protect", "cyan", 30, "start")),
    "<p><b>The payoff:</b> more requests without rewriting the whole service.</p>",
    "Minimal changes require an architecture prepared for horizontal scale.",
    analogy="Adding checkout lanes helps only if every cashier can use the <b>same inventory and payment system.</b>")

s = box(20, 210, 185, 100, "Balancer") + box(340, 45, 235, 100, "Replica A") + box(340, 210, 235, 100, "Replica B") + box(340, 375, 235, 100, "Replica C") + box(730, 205, 190, 130, "State", "Redis / DB", "green", True)
routes = [[(205, 260), (260, 260), (260, y), (340, y)] for y in [95, 260, 425]]
for i, p in enumerate(routes):
    s += arrow(p, f"{i+1}", lx=300, ly=p[-1][1]-18)
for y in [95, 260, 425]:
    s += arrow([(575, y), (660, y), (660, 270), (730, 270)], color="green")
s += text(468, 540, "Any request → any healthy replica", "green", 30)
add('Make replicas <span>interchangeable.</span>', "Stateless = no authoritative user state on one instance.", svg(s, routes),
    "<p><b>Externalize state:</b> sessions in Redis/DB, or signed tokens such as JWTs.</p><p><b>No affinity:</b> a user must not depend on one machine.</p>",
    "Stateless compute, shared state, JWT, load balancing, horizontal scaling.",
    "Requests route to different replicas while state remains shared.")

s = text(25, 40, "ILLUSTRATIVE BOTTLENECK AUDIT", "muted", 24, "start")
for i, (name, value, color) in enumerate([("CPU", .45, "cyan"), ("Memory", .55, "cyan"), ("Connections", .92, "red"), ("DB IOPS", .97, "red")]):
    y = 100+i*103
    s += text(25, y+25, name, anchor="start") + f'<rect x="250" y="{y}" width="535" height="35" rx="10" fill="#1c2440"/><rect x="250" y="{y}" width="{535*value}" height="35" rx="10" fill="{COLORS[color]}"/>' + text(890, y+27, f"{round(value*100)}%", color)
s += text(468, 550, "More app CPUs will not fix saturated storage.", "yellow", 28)
add('Find the <span>actual wall.</span>', "Measure before buying more replicas.", svg(s),
    "<p><b>Inspect:</b> latency, saturation, lock waits and hot partitions.</p><p><b>Choose the right signal:</b> I/O waits can hide behind low CPU.</p>",
    "CPU, memory, connections, DB IOPS, lock contention, hot partitions, wrong scaling metric.")

s = box(20, 220, 165, 100, "Balancer") + box(280, 215, 220, 110, "App replicas", "stateless")
s += box(690, 25, 220, 100, "Cache / state", "Redis", "green") + box(690, 180, 220, 100, "Read replicas", "read-heavy", "purple", True) + box(690, 340, 220, 100, "Primary", "writes", "orange", True) + box(275, 440, 220, 100, "Queue", "durable jobs", "cyan") + box(690, 475, 220, 90, "Workers", "independent", "blue")
s += arrow([(185, 270), (280, 270)])
for y, label, c in [(75, "lookup", "green"), (230, "reads", "purple"), (390, "writes", "orange")]:
    s += arrow([(500, 270), (570, 270), (570, y), (690, y)], label, c, lx=630, ly=y-18)
s += arrow([(385, 325), (385, 440)], "jobs", lx=445, ly=395, dashed=True) + arrow([(495, 520), (690, 520)], "events", lx=590, ly=500, dashed=True)
add('Scale <span>each tier.</span>', "One shared architecture. Different capacity levers.", svg(s),
    "<p><b>Separate paths:</b> cached reads, writes and background jobs.</p><p><b>Legend:</b> solid = synchronous; dashed = async. Read replicas may lag.</p>",
    "Full source architecture, independently scaled workers, state and cache, primary and read replicas.")

s = box(30, 220, 185, 100, "App") + box(355, 220, 220, 100, "Cache", "cache-aside", "green") + box(705, 220, 200, 110, "Read DB", "on a miss", "purple", True)
s += arrow([(215, 270), (355, 270)], "1 lookup", lx=285, ly=244)
s += arrow([(465, 220), (465, 115), (120, 115), (120, 220)], "2 hit: return early", "green", lx=300, ly=90)
s += arrow([(575, 270), (705, 270)], "3 miss", "purple", lx=640, ly=244)
s += arrow([(805, 330), (805, 405), (465, 405), (465, 320)], "4 fill cache + return", "purple", lx=630, ly=445)
s += text(468, 530, "Origin load = requests × (1 − hit rate)", "yellow", 29)
add('Let the <span>cache absorb.</span>', "A hit avoids the database. A miss fetches and fills.", svg(s, [
    [(215, 270), (355, 270), (465, 270), (465, 115), (120, 115), (120, 220)],
    [(215, 270), (355, 270), (575, 270), (705, 270), (805, 330), (805, 405), (465, 405), (465, 320)]]),
    "<p><b>Example:</b> 1,000 req/s at 50% hits → 500 DB reads/s. 10,000 at 90% hits → 1,000: <b>2x, not 10x.</b></p><p><b>Baseline matters:</b> from zero cache hits, 10x at 90% gives 1x origin load.</p>",
    "Cache-aside, hit rate, clarified ~2x claim with explicit baseline.",
    "A cache hit returns early; the next request misses and fills from DB.")

s = box(30, 60, 240, 110, "1 Commit write", "primary DB", "orange", True) + box(350, 60, 240, 110, "2 Invalidate", "cached value", "red") + box(665, 60, 240, 110, "3 Refill", "fresh version", "green")
s += arrow([(270, 115), (350, 115)], color="orange") + arrow([(590, 115), (665, 115)], color="green")
s += box(70, 310, 350, 125, "Racing old reader", "can refill stale data", "red") + box(515, 310, 350, 125, "Bound stale exposure", "version checks / TTL", "green") + arrow([(420, 375), (515, 375)], color="yellow")
s += text(468, 540, "TTL = expiry time; not a consistency guarantee.", "yellow", 27)
add('Give caching a <span>safety story.</span>', "Invalidation is a mechanism, not magic.", svg(s),
    "<p><b>Coherence:</b> define eviction, expiry and stale-read tolerance.</p><p><b>Strict freshness:</b> use a coordinated/versioned strategy or bypass cache; delete-after-write alone can race.</p>",
    "Aggressive but correct cache, coherent invalidation, races and consistency caveat.")

s = ""
for i, (title, detail, color) in enumerate([
    ("1 Offload reads", "Cache + read replicas", "green"),
    ("2 Reuse connections", "Pool before DB overload", "cyan"),
    ("3 Buy time", "Bigger primary / more IOPS", "blue"),
    ("4 Split ownership", "Sharding: highest complexity", "orange")]):
    y = 25+i*138
    s += box(30, y, 355, 105, title, color=color) + arrow([(385, y+52), (475, y+52)], color=color) + box(475, y, 430, 105, detail, color=color)
add('Use <span>cheaper levers</span> first.', "The database often sets the ceiling.", svg(s),
    "<p><b>Read-heavy:</b> try cache and replicas before partitioning.</p><p><b>Workload-dependent:</b> read offload does not solve a write-bound primary.</p>",
    "Ordered database levers: cache/read replicas, PgBouncer, vertical bump, sharding last.")

s = box(20, 200, 190, 110, "App", "10 jobs/s") + box(325, 155, 290, 210, "Queue", "", "cyan") + box(745, 200, 175, 110, "Workers", "6 → 12/s", "blue")
s += arrow([(210, 255), (325, 255)], "enqueue", lx=270, ly=228, dashed=True) + arrow([(615, 255), (745, 255)], "consume", lx=680, ly=228, dashed=True)
for i in range(6):
    s += f'<rect id="job{i}" x="{350+i*40}" y="290" width="28" height="40" rx="5" fill="#ffd166"/>'
s += text(468, 100, "Arrival > processing → backlog grows", "yellow", 29)
s += text(468, 450, "Scale workers → processing > arrival → drain", "green", 28)
s += text(468, 530, "Illustrative rates and compressed time", "muted", 24)
dynamic = """const count = t < .7 ? 1 : t < 2.8 ? Math.min(6,1+Math.floor((t-.7)*2.5)) : t < 5 ? Math.max(0,6-Math.floor((t-2.8)*3)) : 0;
for(let i=0;i<6;i++) document.getElementById('job'+i).style.opacity = i<count ? '1' : '.12';"""
add('Move slow work <span>off-path.</span>', "Respond after required work; enqueue everything else.", svg(s, [[(210,255),(325,255)], [(615,255),(745,255)]], dynamic),
    "<p><b>Good candidates:</b> email, indexing and analytics.</p><p><b>Delivery safety:</b> durable enqueue, retries and idempotent workers. Scale from queue age/depth, not just CPU.</p>",
    "Async noncritical work, independent worker scale, backpressure and durability.",
    "Backlog grows at 10 arrivals versus 6 completions, then drains with 12 completions.")

s = box(30, 35, 225, 100, "Replica A", "pool ≤ 20") + box(30, 220, 225, 100, "Replica B", "pool ≤ 20") + box(30, 405, 225, 100, "Replica N", "pool ≤ 20")
s += box(380, 220, 245, 110, "DB pooler", "e.g. PgBouncer") + box(730, 220, 190, 130, "Database", "finite slots", "orange", True)
for y in [85, 270, 455]:
    s += arrow([(255,y),(315,y),(315,275),(380,275)])
s += arrow([(625,275),(730,275)], color="orange")
s += text(468, 560, "10 replicas × 20 slots = up to 200 app connections", "yellow", 26)
add('Budget <span>connections</span> globally.', "More replicas can multiply database pressure.", svg(s),
    "<p><b>Bound the total:</b> app pools + workers + admin reserve must fit DB capacity.</p><p><b>Pooler caveat:</b> transaction pooling may change session-level behavior; check compatibility.</p>",
    "Connection exhaustion, connection pooling PgBouncer, global budget and warm connection pools.")

s = box(25, 60, 225, 110, "Read traffic", "can fan out", "purple") + box(380, 30, 235, 110, "Replica 1", "", "purple", True) + box(675, 30, 235, 110, "Replica N", "", "purple", True)
s += arrow([(250,115),(320,115),(320,85),(380,85)], color="purple") + arrow([(250,115),(320,115),(320,205),(790,205),(790,140)], color="purple")
s += box(25, 295, 225, 110, "10x writes", "one owner", "orange") + box(385, 290, 235, 130, "Primary", "write ceiling", "red", True)
s += arrow([(250,350),(385,350)], color="orange")
s += text(770, 345, ["Read replicas", "do not multiply", "write capacity."], "red")
s += text(468, 530, "Then: optimize writes, resize, shard or change store.", "green", 27)
add('Reads scale. <span>Writes resist.</span>', "One primary still owns the write stream.", svg(s),
    "<p><b>Sharding:</b> divide data across independent write owners.</p><p><b>Watch hot keys:</b> uneven partitions can preserve the bottleneck; a write-optimized store may fit better.</p>",
    "Primary DB write ceiling, read replicas do not offload writes, sharding and write-optimized store, hot partitions.")

s = box(30, 210, 235, 120, "Primary", "", "orange", True) + box(665, 210, 235, 120, "Read replica", "", "purple", True)
s += text(147, 300, "version 42", "orange", 24)
s += text(782, 300, "41 → 42", "purple", 24, id="version")
s += arrow([(265,265),(665,265)], "replication takes time", "purple", lx=465, ly=232, dashed=True)
s += box(350, 405, 235, 100, "User reads", "after own write", "cyan")
s += arrow([(585,455),(782,455),(782,330)], "may be stale", "red", lx=770, ly=490)
s += arrow([(350,455),(147,455),(147,330)], "read own write", "green", lx=160, ly=490)
s += text(468, 90, "Write accepted ≠ replica caught up", "yellow", 30)
add('Respect <span>replica lag.</span>', "Replication is a delayed copy, not an instant mirror.", svg(s, [[(265,265),(665,265)]],
    "document.getElementById('version').textContent=t<4.3?'version 41 · stale':'version 42 · fresh';"),
    "<p><b>Read-your-writes:</b> route to primary and bypass stale cache.</p><p><b>Alternative:</b> wait for a replica watermark covering the write; a timestamp alone is not enough.</p>",
    "Replica lag, stale read-after-write, primary routing and logical timestamp/watermark gate.",
    "The replica remains stale until replication arrives; primary serves the writer's fresh read.")

s = box(30, 185, 225, 130, "New replicas", "cold local caches", "cyan") + box(380, 185, 215, 130, "Cold pools", "many openings", "yellow") + box(730, 185, 190, 130, "Database", "sudden spike", "red", True)
s += arrow([(255,250),(380,250)], color="yellow") + arrow([(595,250),(730,250)], color="red")
s += text(468, 85, "Cold scale-up can become a thundering herd.", "red", 28)
s += box(35, 410, 270, 110, "Warm gradually", "cache + connections", "green") + box(335, 410, 270, 110, "Merge misses", "single-flight", "green") + box(635, 410, 270, 110, "Spread expiry", "TTL jitter", "green")
add('Warm capacity <span>before routing.</span>', "A replica can be running but not ready for full load.", svg(s, [
    [(255,235),(380,235),(595,235),(730,235)], [(255,250),(380,250),(595,250),(730,250)], [(255,265),(380,265),(595,265),(730,265)]]),
    "<p><b>Readiness:</b> ramp traffic after bounded warmup, with DB headroom.</p><p><b>Cache nuance:</b> a shared Redis cache may stay warm; local optional caches and connection pools do not.</p>",
    "Cold cache and connection pool herd on scale-up, prewarm and headroom, non-authoritative local cache nuance.",
    "Several cold replicas open/fetch concurrently, showing a burst toward the DB.")

s = text(35, 55, "METRIC → DECISION → BOOT → WARM → READY", "cyan", 28, "start")
s += arrow([(65,270),(890,270)], color="muted")
for x, label in [(85,"burst"),(310,"sample"),(525,"scale"),(725,"warm"),(865,"ready")]:
    s += f'<circle cx="{x}" cy="270" r="9" fill="#4dd8e6"/>' + text(x, 315, label, "muted", 24)
s += f'<path d="M85 250 L85 120 L390 120 L390 250" fill="none" stroke="{COLORS["red"]}" stroke-width="5"/>'
s += text(240, 95, "demand arrives first", "red", 26)
s += box(80, 395, 335, 115, "Choose true signal", "CPU / concurrency / queue", "cyan") + box(505, 395, 335, 115, "Avoid flapping", "stabilize + cooldown", "green")
add('Autoscaling has <span>a delay.</span>', "The traffic spike does not wait for the next metric sample.", svg(s, [[(85,270),(865,270)]]),
    "<p><b>Absorb the lag:</b> pre-warm for known peaks and retain headroom.</p><p><b>Reduce oscillation:</b> stabilization windows and cautious scale-down prevent connection churn.</p>",
    "Metric/scale/warmup lag, wrong metric when I/O-bound, prewarming, overprovisioning, autoscaler oscillation cost.",
    "A marker traverses the scaling timeline only after demand has already spiked.")

s = box(25, 220, 210, 110, "Traffic burst", "beyond capacity", "orange") + box(370, 220, 220, 110, "Admission", "bound concurrency", "cyan") + box(730, 105, 190, 110, "Service", "accepted", "green")
s += box(710, 415, 210, 105, "Reject / defer", "explicit response", "red")
s += arrow([(235,275),(370,275)], color="orange") + arrow([(590,275),(645,275),(645,160),(730,160)], "within budget", "green", lx=780, ly=245)
s += arrow([(480,330),(480,467),(710,467)], "excess", "red", lx=595, ly=435)
s += text(468, 70, "Small bounded queue > unbounded waiting", "yellow", 29)
add('Protect the <span>useful capacity.</span>', "Headroom buys time. Admission control prevents collapse.", svg(s, [
    [(235,275),(370,275),(590,275),(645,275),(645,160),(730,160)],
    [(235,275),(370,275),(480,330),(480,467),(710,467)]]),
    "<p><b>Under overload:</b> cap work, enforce deadlines, shed low-priority load.</p><p><b>Tell clients:</b> 429/503 where appropriate; retries need backoff and jitter, or amplify the spike.</p>",
    "Spikes outrun autoscaling, headroom, load shedding, bounded queues and retry amplification.",
    "Within-budget work reaches the service; excess is explicitly rejected rather than piling up.")

s = box(15, 220, 180, 100, "Client + LB") + box(285, 220, 190, 100, "App") + box(690, 30, 220, 100, "Cache", "hit returns", "green") + box(690, 200, 220, 115, "Read DB", "miss fetch", "purple", True) + box(690, 375, 220, 115, "Primary", "write commit", "orange", True) + box(285, 445, 290, 110, "Queue → workers", "background jobs", "blue")
s += arrow([(195,270),(285,270)], "request", lx=240, ly=242)
s += arrow([(475,270),(560,270),(560,80),(690,80)], "1 read", "green", lx=620, ly=53)
s += arrow([(800,130),(800,200)], "2 miss", "purple", lx=863, ly=173)
s += arrow([(475,270),(620,270),(620,430),(690,430)], "write", "orange", lx=650, ly=365)
s += arrow([(380,320),(380,445)], "enqueue", "blue", lx=460, ly=392, dashed=True)
add('Follow <span>one request.</span>', "Branch by work type. Do not force every hop onto every path.", svg(s, [
    [(195,270),(285,270),(475,270),(560,270),(560,80),(690,80)],
    [(195,270),(285,270),(475,270),(620,270),(620,430),(690,430)],
    [(380,320),(380,445)]]),
    "<p><b>Read:</b> check cache, then read DB on a miss; refill and return.</p><p><b>Write + jobs:</b> commit required state; durably hand off jobs before claiming acceptance. Dashed = async.</p>",
    "End-to-end request branches, cache miss/read replicas, primary writes, asynchronous workers.",
    "A read takes the cache branch; a write takes the primary branch, followed by background handoff.")

s = text(35, 40, "RISK", "red", 24, "start") + text(355, 40, "WHAT BREAKS", "muted", 24, "start") + text(675, 40, "FIX", "green", 24, "start")
for i, (risk, impact, fix) in enumerate([
    (["Sticky sessions", "local files"], ["Replica loss", "loses user state"], ["Shared state", "object storage"]),
    (["Local cache", "as truth"], ["Replicas disagree", "on correctness"], ["Authoritative store", "cache optional"]),
    (["Hot partition", "lock contention"], ["One owner", "still saturates"], ["Spread hot keys", "shorter transactions"]),
    (["Pool exhaustion", "scale-down churn"], ["Upstream waits", "cascade"], ["Global budgets", "graceful drain"])]):
    y = 78+i*125
    s += f'<rect x="20" y="{y}" width="900" height="108" rx="14" fill="#161d33" stroke="#2b3658"/>'
    s += text(35, y+40, risk, "red", 24, "start") + text(355, y+40, impact, size=24, anchor="start") + text(675, y+40, fix, "green", 24, "start")
add('Remove <span>hidden limits.</span>', "Scaling exposes assumptions that ordinary traffic hides.", svg(s),
    "<p><b>Failure drill:</b> remove a replica during peak load. Users should keep working.</p><p><b>Do not confuse:</b> more nodes with more usable end-to-end capacity.</p>",
    "All failure modes including hidden state, local caches, sticky sessions, disk files, locks, hot partitions, exhaustion and churn.")

s = ""
for i, (name, detail, color) in enumerate([
    ("Baseline", "measure current path", "cyan"),
    ("10x test", "real read/write mix", "orange"),
    ("Hold load", "lag + backlog + cost", "yellow"),
    ("Roll out", "gradual traffic ramp", "green")]):
    y = 25+i*137
    s += box(25, y, 300, 100, name, color=color) + arrow([(325,y+50),(430,y+50)], color=color) + box(430,y,480,100,detail,color=color)
add('Prove <span>10x</span> end-to-end.', "Minimal changes are useful only if the whole path survives.", svg(s),
    "<p><b>Acceptance:</b> meet your latency/error targets with bounded queues, DB saturation and cost.</p><p><b>Exercise edges:</b> cold start, stale reads, burst then scale-down. Stop or roll back if budgets fail.</p>",
    "Validation of scale under real bottleneck metrics, warming, lag, flapping, headroom, cost; operational synthesis.")

add('Scale <span>without surprises.</span>', "Five rules to keep the design honest.", ("", [], ""),
    "", "Recap and all four source references.")

SOURCES = [
    ("Netflix · Zuul 2 edge tier", "https://netflixtechblog.com/open-sourcing-zuul-2-82ea476cb2b3"),
    ("Discord · billions of messages", "https://discord.com/blog/how-discord-stores-billions-of-messages"),
    ("Instagram · Postgres sharding", "https://instagram-engineering.com/sharding-ids-at-instagram-1cf5a71e5a5c"),
    ("AWS · Performance Efficiency", "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html"),
]

NODE = r"""
(async () => {
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn, spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'carousel-chrome-'));
const framesRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'carousel-frames-'));
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
 ['--headless=new','--disable-gpu','--hide-scrollbars','--remote-debugging-port=0',
  '--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`],
 {stdio:'ignore'});
let ws;
let id=0;
const pending = new Map();
const sleep = ms => new Promise(r=>setTimeout(r,ms));
async function call(method, params={}) {
 const key=++id;
 return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{pending.delete(key);reject(new Error(`CDP timeout: ${method}`));},30000);
  pending.set(key,{resolve,reject,timer});
  ws.send(JSON.stringify({id:key,method,params}));
 });
}
async function evaluate(expression) {
 const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
 if(r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
 return r.result.value;
}
async function shot(file, scale=1) {
 const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,
  clip:{x:0,y:0,width:1080,height:1350,scale}});
 fs.writeFileSync(file,Buffer.from(r.data,'base64'));
}
try {
 let port;
 for(let attempt=0;attempt<100;attempt++){
  if(chrome.exitCode !== null) throw new Error('Chrome exited before becoming ready');
  const p=path.join(profile,'DevToolsActivePort');
  if(fs.existsSync(p)){port=fs.readFileSync(p,'utf8').split('\n')[0];break;}
  await sleep(100);
 }
 if(!port) throw new Error('Chrome did not become responsive');
 const base=`http://127.0.0.1:${port}`;
 const tab=await (await fetch(`${base}/json/new?about:blank`,{method:'PUT'})).json();
 ws=new WebSocket(tab.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true});});
 ws.addEventListener('message',ev=>{
  const m=JSON.parse(ev.data);const p=pending.get(m.id);if(!p)return;
  clearTimeout(p.timer);pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);
 });
 await call('Page.enable');await call('Runtime.enable');
 for(const slide of manifest.slides){
  await call('Emulation.setDeviceMetricsOverride',{width:1080,height:1350,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:pathToFileURL(slide.file).href});
  for(let tries=0;tries<100;tries++){
   if(await evaluate(`document.readyState==='complete' && typeof window.renderFrame==='function'`))break;
   if(tries===99)throw new Error('Page readiness timed out');
   await sleep(30);
  }
  await evaluate('document.fonts.ready.then(()=>true)');
  const errors = await evaluate(`(()=>{
   const errors=[];const footer=document.querySelector('.footer').getBoundingClientRect();
   for(const el of document.querySelectorAll('h1,.sub,.notes,.analogy,.resources,.recap,.footer,.kicker')){
    const r=el.getBoundingClientRect();
    if(r.left<71||r.right>1009||r.bottom>1281)errors.push(el.className+' outside safe area');
    if(!el.classList.contains('footer') && r.bottom>footer.top-20)errors.push(el.className+' hits footer');
   }
   for(const el of document.querySelectorAll('svg text')){
    const r=el.getBoundingClientRect();
    const scene=el.closest('svg').getBoundingClientRect();
    if(r.left<72||r.right>1008||r.top<scene.top||r.bottom>scene.bottom)errors.push(el.textContent+' outside scene');
   }
   return errors;
  })()`);
  if(errors.length)throw new Error(`Slide ${slide.number}: ${errors.join('; ')}`);
  await shot(path.join(manifest.out,`${slide.number}.png`),2);
  console.log(`PNG ${slide.number}/${manifest.slides.length}`);
  if(!slide.animated)continue;
  const dir=path.join(framesRoot,String(slide.number));fs.mkdirSync(dir);
  for(let f=0;f<60;f++){
   await evaluate(`window.renderFrame(${f/10}); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
   await shot(path.join(dir,`${String(f).padStart(4,'0')}.png`));
  }
  const result=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-framerate','10',
   '-i',path.join(dir,'%04d.png'),'-filter_complex',
   '[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a',
   '-loop','0',path.join(manifest.out,`${slide.number}.gif`)],{encoding:'utf8',timeout:120000});
  if(result.status!==0)throw new Error(result.stderr||String(result.error));
  console.log(`GIF ${slide.number}: 6 seconds at 10 fps`);
 }
 console.log(`Reviewed frame sequences retained for inspection: ${framesRoot}`);
} finally {
 if(ws && ws.readyState===WebSocket.OPEN){try{await call('Browser.close');}catch(e){console.error(e.message);}ws.close();}
 if(chrome.exitCode===null)chrome.kill('SIGTERM');
 await sleep(500);
 fs.rmSync(profile,{recursive:true,force:true});
}
})().catch(error => { console.error(error); process.exitCode=1; });
"""


def page(slide):
    n = slide["number"]
    recap = ""
    if n == TOTAL:
        recap = '<div class="recap">' + "".join(f'<div class="rule">{rule}</div>' for rule in [
            "1. Stateless replicas share authoritative state.",
            "2. Measure the bottleneck before scaling.",
            "3. Cache reads; protect the write primary.",
            "4. Queue noncritical work with safe delivery.",
            "5. Warm, bound and validate every tier.",
        ]) + '</div><div class="resources"><b>Read the real-world engineering stories</b><br>' + "<br>".join(
            f'<a href="{url}">{label}</a>' for label, url in SOURCES) + '</div><div class="analogy">Save for your next design discussion.<br><b>Follow @engineering.by.heart</b></div>'
    paths = json.dumps(slide["paths"])
    script = f"""
<script>
const routes={paths};
function along(points,u){{
 const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
 let d=u*lengths.reduce((a,b)=>a+b,0);
 for(let i=0;i<lengths.length;i++){{if(d<=lengths[i]){{const v=d/lengths[i];return [points[i][0]+v*(points[i+1][0]-points[i][0]),points[i][1]+v*(points[i+1][1]-points[i][1])];}}d-=lengths[i];}}
 return points[points.length-1];
}}
window.renderFrame=t=>{{
 const active=t>=.7&&t<4.8;
 routes.forEach((p,i)=>{{
  const token=document.getElementById('token'+i);
  let u;
  if({n}===12)u=(t-.7)/3.3;
  else if(routes.length===1)u=(t-.7)/3.6;
  else u=((t-.7)/(4.1/routes.length))-i;
  const visible=active&&u>=0&&u<=1;
  token.setAttribute('visibility',visible?'visible':'hidden');
  if(visible){{const [x,y]=along(p,u);token.setAttribute('cx',x);token.setAttribute('cy',y);}}
 }});
 {slide["dynamic"]}
}};
</script>"""
    return "<!doctype html><html><head>" + STYLE + "</head><body>" + f"""
<div class="kicker"><span class="dot"></span>Scaling · {n:02d} / {TOTAL:02d}</div>
<h1>{slide["title"]}</h1><div class="sub">{slide["subtitle"]}</div>
{slide["scene"]}
{f'<div class="analogy">{slide["analogy"]}</div>' if slide["analogy"] else ""}
<div class="notes">{slide["notes"]}</div>{recap}
<div class="spacer"></div><div class="footer"><div><span class="brand">@engineering.by.heart</span> · System Design</div><div><span class="page">{n:02d}/{TOTAL:02d}</span> &nbsp; <span class="swipe">{"SAVE" if n == TOTAL else "SWIPE →"}</span></div></div>
""" + script + "</body></html>"


def main():
    if len(SLIDES) != TOTAL or not 2 <= TOTAL <= 20:
        raise ValueError("Storyboard must contain 2–20 complete slides")
    expected = {f"{n}.png" for n in range(1, TOTAL+1)} | {
        f'{s["number"]}.gif' for s in SLIDES if s["motion"]}
    stale = [p.name for p in OUT.iterdir() if p.suffix.lower() in {".png", ".gif", ".jpg", ".jpeg", ".webp"} and p.name not in expected]
    if stale:
        raise ValueError(f"Unexpected media would change publisher discovery: {stale}")
    with tempfile.TemporaryDirectory(prefix="carousel-build-") as tmp:
        work = Path(tmp)
        manifest = dict(out=str(OUT), slides=[])
        for slide in SLIDES:
            file = work / f'{slide["number"]}.html'
            file.write_text(page(slide))
            manifest["slides"].append(dict(number=slide["number"], file=str(file), animated=bool(slide["motion"])))
        (work / "manifest.json").write_text(json.dumps(manifest))
        (work / "render.cjs").write_text(NODE)
        subprocess.run(["node", str(work / "render.cjs"), str(work / "manifest.json")], check=True, timeout=1200)
    print(f"Done: {TOTAL} PNGs and {sum(bool(s['motion']) for s in SLIDES)} GIFs in {OUT}")


if __name__ == "__main__":
    main()

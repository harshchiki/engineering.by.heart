#!/usr/bin/env python3
"""Render a source-grounded Course Schedule carousel and deterministic GIFs."""
import base64
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request

from PIL import Image

OUT = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
THEME = "Data Structions & Algorithms"
TOTAL = 18
FPS = 10
DURATION = 6
COLORS = {
    "ink": "#eaf0ff", "muted": "#9aa7c7", "cyan": "#4dd8e6",
    "green": "#36d399", "red": "#ff4d5e", "orange": "#ff9a3d",
    "yellow": "#ffd166", "purple": "#b592ff", "blue": "#5aa9ff",
}

# The storyboard preserves the method, its data structures, and every test family.
# Static scenes show the complete lesson; only causal state transitions animate.
STORYBOARD = [
    ("Finish every course?", "Boolean goal; prerequisite analogy", "unlockable course graph", None),
    ("Read the arrow correctly", "pair[1] -> pair[0]; higher-numbered prerequisites", "pair-to-edge translation", None),
    ("Count unfinished prerequisites", "indegree definition; multiple prerequisites", "three incoming arrows", None),
    ("Three tools, one graph", "Map<Integer, Set<Integer>>, int[], ArrayDeque", "graph / counts / ready queue", None),
    ("Build each edge once", "computeIfAbsent; Set.add gates indegree increment", "duplicate pair with one edge", None),
    ("Start with unlocked courses", "scan every ID; isolated/disconnected vertices", "graph and initial ready queue", None),
    ("Take one ready course", "poll; completedCourses++; ready invariant", "queue to completed lane", "FIFO removal changes progress, not counts"),
    ("Release its dependents", "decrement each outgoing dependent; shared prerequisite", "fan-out with before/after counters", "one completion releases two prerequisite edges"),
    ("Zero means ready", "enqueue only at zero; diamond dependencies", "two prerequisites converge", "first decrement waits; second unlocks the course"),
    ("Follow the whole queue", "diamond traversal; O(V+E) process", "graph, ready queue, completed timeline", "queue and counters evolve together"),
    ("A cycle locks everything", "two-course and three-course cycles; false", "cycle with no ready vertex", None),
    ("Blocked is not always cyclic", "cycle with dependent; cycle in disconnected group", "cyclic core, blocked tail, completed group", None),
    ("Why the count proves it", "Kahn correctness; DAG meaning; count equals V", "acyclic removal versus cyclic remainder", None),
    ("Build the Java graph", "exact source construction and deduplication", "source excerpt with semantic gloss", None),
    ("Run the Java loop", "source queue, decrement, emptySet, return", "source excerpt with invariant", None),
    ("Linear work, linear storage", "expected time; worst-case auxiliary space", "vertices and unique edge visits", None),
    ("Check the sharp edges", "all 16 source test families; valid-input assumptions", "edge-case mini graphs and matrix", None),
    ("Keep these five rules", "recap; source and Kahn resources; CTA", "five-step dependency strip", None),
]
assert len(STORYBOARD) == TOTAL and 2 <= TOTAL <= 20

STYLE = """
<meta charset="utf-8">
<style>
:root{--red:#ff4d5e;--orange:#ff9a3d;--green:#36d399;--cyan:#4dd8e6;--yellow:#ffd166;--purple:#b592ff;--blue:#5aa9ff;--ink:#eaf0ff;--muted:#9aa7c7;--card:#161d33;--line:#2b3658}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px}
body{font-family:"Helvetica Neue",Arial,sans-serif;background:radial-gradient(1200px 700px at 15% -10%,#1a2b4d 0%,transparent 60%),radial-gradient(1000px 800px at 110% 10%,#241433 0%,transparent 55%),linear-gradient(160deg,#0a0e1c,#0d1428 55%,#0a1020);color:var(--ink);padding:74px 72px 70px;display:flex;flex-direction:column;overflow:hidden}
.kicker{display:flex;align-items:center;gap:14px;font-size:26px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--red)}
.dot{width:14px;height:14px;border-radius:50%;background:var(--red);box-shadow:0 0 18px var(--red);flex-shrink:0}
h1{font-size:76px;line-height:1.02;font-weight:900;letter-spacing:-1px;margin-top:24px}
.hl{color:var(--orange)}.hlg{color:var(--green)}.hlc{color:var(--cyan)}
.sub{font-size:31px;line-height:1.4;color:var(--muted);margin-top:24px}
.diagram{display:block;width:936px;height:auto;margin-top:26px;flex-shrink:0}
.diagram text{font-family:"Helvetica Neue",Arial,sans-serif;font-size:28px;font-weight:600;fill:var(--ink)}
.diagram .small{font-size:24px;fill:var(--muted)}.diagram .big{font-size:38px;font-weight:800}
.analogy,.callout{background:linear-gradient(90deg,rgba(255,154,61,.14),rgba(255,77,94,.06));border:1px solid var(--line);border-left:7px solid var(--orange);border-radius:20px;padding:25px 30px;margin-top:25px;font-size:30px;line-height:1.4}
.callout{border-left-color:var(--green);background:var(--card)}
b{color:var(--ink)}.analogy b{color:var(--orange)}
.note{font-size:26px;line-height:1.4;color:var(--muted);margin-top:24px}
.note b{color:var(--yellow)}
.spacer{flex:1 1 auto}
.footer{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--line);padding-top:22px;margin-top:28px;flex-shrink:0;font-size:25px;color:var(--muted)}
.brand{font-weight:800;color:var(--ink)}.theme{font-size:24px;margin-top:5px}
.pageno{color:var(--red);font-weight:800}.swipe{color:var(--orange);font-weight:800;font-size:24px}
pre{font-family:Menlo,Consolas,monospace;font-size:25px;line-height:1.6;white-space:pre;margin-top:28px;padding:28px 26px;border:1px solid var(--line);border-radius:22px;background:var(--card);color:#d7e0f7}
code{font-family:Menlo,Consolas,monospace}.kw{color:var(--purple)}.good{color:var(--green)}.accent{color:var(--cyan)}
table{width:100%;border-collapse:separate;border-spacing:0 12px;margin-top:18px}
th{font-size:24px;color:var(--muted);text-align:left;padding:0 16px}
td{font-size:26px;line-height:1.35;padding:19px 16px;background:var(--card)}
td:first-child{border-left:5px solid var(--red);border-radius:12px 0 0 12px}td:last-child{color:var(--green);border-radius:0 12px 12px 0}
.rules{font-size:30px;line-height:1.45;margin-top:25px;list-style:none}.rules li{margin-top:14px}.rules b{color:var(--green)}
.resource{font-size:24px;line-height:1.4;margin-top:23px;color:var(--muted)}
</style>
"""


def text(x, y, value, color=None, cls="", anchor="middle", id=None):
    attrs = f' class="{cls}"' if cls else ""
    if id:
        attrs += f' id="{id}"'
    if color:
        attrs += f' style="fill:{COLORS.get(color, color)}"'
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}"{attrs}>{html.escape(str(value))}</text>'


def node(x, y, name, color="cyan", label=None, id=None, radius=43):
    c = COLORS[color]
    attrs = f' id="{id}"' if id else ""
    return f'<g{attrs}><circle cx="{x}" cy="{y}" r="{radius}" fill="#161d33" stroke="{c}" stroke-width="4"/>{text(x,y+12,name,cls="big")}{text(x,y+radius+37,label,color="muted",cls="small") if label else ""}</g>'


def arrow(x1, y1, x2, y2, color="cyan", label=None, id=None, dashed=False):
    attrs = f' id="{id}"' if id else ""
    dash = ' stroke-dasharray="9 9"' if dashed else ""
    return f'<g{attrs}><path d="M{x1},{y1} L{x2},{y2}" stroke="{COLORS[color]}" stroke-width="4" fill="none" marker-end="url(#{color})"{dash}/>{text((x1+x2)/2,(y1+y2)/2-18,label,color,cls="small") if label else ""}</g>'


def panel(x, y, w, h, label=None, color="cyan"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="#161d33" stroke="#2b3658" stroke-width="2"/>{text(x+24,y+42,label,color,anchor="start") if label else ""}'


def svg(content, height=560):
    markers = "".join(f'<marker id="{name}" markerWidth="9" markerHeight="9" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8" fill="{value}"/></marker>' for name, value in COLORS.items())
    return f'<svg class="diagram" viewBox="0 0 936 {height}" role="img" aria-label="Course prerequisite diagram"><defs>{markers}</defs>{content}</svg>'


POS = {0: (125, 240), 1: (445, 110), 2: (445, 370), 3: (765, 240)}
EDGES = [(0, 1), (0, 2), (1, 3), (2, 3)]


def diamond(counts=(0, 1, 1, 2), completed=(), numbered=False):
    parts = []
    for a, b in EDGES:
        x1, y1 = POS[a]
        x2, y2 = POS[b]
        d = math.hypot(x2-x1, y2-y1)
        dx, dy = (x2-x1)/d*51, (y2-y1)/d*51
        parts.append(arrow(x1+dx,y1+dy,x2-dx,y2-dy,id=f"edge{a}{b}",color="muted" if a in completed else "cyan"))
    for n, (x, y) in POS.items():
        parts.append(node(x,y,n,color="green" if n in completed else "cyan",id=f"node{n}"))
        label = "DONE" if n in completed else f"indegree = {counts[n]}"
        parts.append(text(x,y+82,label,"green" if n in completed else "muted",cls="small",id=f"count{n}"))
    if numbered:
        parts.append(text(468,490,"One valid completion order: 0 → 1 → 2 → 3","green"))
    return "".join(parts)


def row_slots(x, y, items, title, color="cyan", width=96, id_prefix="slot"):
    parts = [text(x,y-24,title,color,anchor="start")]
    for i, val in enumerate(items):
        xx = x+i*(width+14)
        parts.append(f'<rect x="{xx}" y="{y}" width="{width}" height="68" rx="13" fill="#1c2440" stroke="{COLORS[color]}" stroke-width="2"/>')
        parts.append(text(xx+width/2,y+44,val,id=f"{id_prefix}{i}"))
    return "".join(parts)


def footer(n):
    cue = "SAVE + FOLLOW" if n == TOTAL else "SWIPE →"
    return f'<div class="spacer"></div><div class="footer"><div><div class="brand">@engineering.by.heart</div><div class="theme">{THEME}</div></div><div><span class="pageno">{n:02d}/{TOTAL:02d}</span> &nbsp; <span class="swipe">{cue}</span></div></div>'


slides = {}
animations = {}


def slide(n, title, sub, content, note="", script=""):
    slides[n] = f'<div class="kicker"><span class="dot"></span>{THEME}</div><h1>{title}</h1><div class="sub">{sub}</div>{content}{f"""<div class="note">{note}</div>""" if note else ""}{footer(n)}'
    animations[n] = script


slide(1, 'Can you finish <span class="hl">every course?</span>',
      "Course Schedule I · Kahn's topological sort",
      '<div class="analogy">Courses are <b>locked doors</b>. Finish the prerequisites to unlock the next one.</div>' +
      svg(node(150,140,0,"green",label="ready now") +
          arrow(205,140,407,140,label="unlocks") +
          node(468,140,1,label="after course 0") +
          arrow(523,140,725,140,label="unlocks") +
          node(785,140,2,label="after course 1") +
          text(468,310,"Finish 0 → unlock 1 → unlock 2","green"),400) +
      '<div class="callout"><b>The payoff:</b> turn “Can I finish?” into a graph, a queue, and one final count.</div>')

slide(2, 'Point arrows <span class="hl">forward</span>',
      "A prerequisite pair is [course, requiredCourse].",
      svg(panel(130,30,676,120) + text(468,105,"[1, 0]","orange",cls="big") +
          text(260,212,"requiredCourse","muted") + text(680,212,"course","muted") +
          arrow(315,300,625,300,label="must finish before") +
          node(260,300,0,label="prerequisite") + node(680,300,1,label="dependent") +
          panel(78,426,780,106) + text(468,471,"[0, 3] means 3 → 0","green") +
          text(468,509,"Course IDs do not determine completion order.",cls="small")),
      '<b>Fresher tip:</b> an arrow is a rule, not a path you must physically travel.')

slide(3, 'Count <span class="hl">unfinished</span> prerequisites',
      "Indegree = how many prerequisite edges still block a course.",
      svg(arrow(232,110,655,236) + arrow(232,280,655,280) + arrow(232,450,655,324) +
          node(180,110,0) + node(180,280,1) + node(180,450,2) +
          node(720,280,3,color="orange",radius=62) +
          text(720,408,"indegree[3] = 3","orange") +
          text(180,533,"Three prerequisites",cls="small") +
          text(720,533,"Not ready yet",color="yellow",cls="small")),
      '<b>Ready means zero.</b> A course can start only when no prerequisite remains unfinished.')

slide(4, 'Use <span class="hl">three tools</span>',
      "Store the graph, track its locks, process ready courses.",
      svg(panel(0,0,936,178,"1 / relations: prerequisite → dependents") +
          node(122,99,0,radius=32) + arrow(165,99,328,99) +
          text(470,111,"{1, 2}","cyan",cls="big") +
          text(710,105,"Map + Set",color="muted") +
          panel(0,196,936,158,"2 / indegree: remaining prerequisites","orange") +
          row_slots(44,266,["0","1","1","2"],"","orange",id_prefix="counts") +
          text(720,310,"int[numCourses]",color="muted") +
          panel(0,372,936,158,"3 / readyCourses: only zero-indegree courses","green") +
          row_slots(44,442,["0"],"","green") +
          text(590,484,"Queue / ArrayDeque",color="muted")),
      '<b>IDs are array indexes:</b> courses run from 0 to numCourses − 1.')

slide(5, 'Add each dependency <span class="hl">once</span>',
      "The source uses a Set to ignore repeated prerequisite pairs.",
      svg(panel(0,25,340,340,"Input pairs","orange") +
          text(170,132,"[1, 0]","orange",cls="big") +
          text(170,218,"[1, 0]","orange",cls="big") +
          text(170,308,"Same rule twice",cls="small") +
          arrow(365,198,505,198,label="deduplicate") +
          node(576,198,0) + arrow(627,198,794,198) + node(852,198,1) +
          text(716,324,"ONE unique edge","green") +
          panel(0,401,936,130) +
          text(468,452,"Set.add(course) is true only for a new edge.","green") +
          text(468,498,"Only then does indegree[course] increase.",cls="small")),
      '<b>Keep both structures aligned.</b> Counting two edges but storing one would leave a valid course blocked.')

slide(6, 'Queue every <span class="hlg">unlocked</span> course',
      "Scan all course IDs, not just keys in the adjacency map.",
      svg(node(115,123,0,label="indegree 0",color="green") +
          arrow(167,123,354,123) + node(410,123,1,label="indegree 1") +
          node(680,123,2,label="indegree 0",color="green") +
          text(680,240,"Isolated course",cls="small") +
          arrow(115,220,115,362,"green") + arrow(680,265,310,362,"green") +
          row_slots(68,396,["0","2"],"Initial queue: [0, 2]","green",width=125) +
          text(635,447,"Course 1 waits.",color="yellow") +
          text(468,533,"All components matter. An isolated course still counts.",cls="small")),
      '<b>No prerequisites?</b> Every course enters the queue and the answer is true.')

slide(7, 'Take one <span class="hlg">ready course</span>',
      "poll() removes the queue head. Then completedCourses increases.",
      svg(panel(0,0,936,530) +
          row_slots(50,140,["0","2"],"BEFORE · ready queue","cyan",width=140,id_prefix="q") +
          text(665,68,"poll() → complete","green") +
          arrow(120,222,120,268,"green") + arrow(163,270,650,270,"green") +
          node(740,270,0,"green",id="moving") +
          text(740,350,"completed","muted",cls="small",id="movingLabel") +
          row_slots(50,402,["2"],"AFTER · ready queue","green",width=140,id_prefix="after") +
          text(620,416,"completedCourses: 0 → 1","green",id="progress") +
          text(468,494,"A queued course has no unfinished prerequisites.",cls="small")),
      '<b>The invariant:</b> every polled course is safe to complete.',
      script="""
const moving=document.getElementById('moving');
const q0=document.getElementById('q0');
const after=document.getElementById('after0');
const progress=document.getElementById('progress');
window.renderFrame=t=>{
 const phase=t<0.8?0:t<3.2?(t-0.8)/2.4:t<5.4?1:0;
 const x=phase<0.25?120:120+(phase-0.25)/0.75*620;
 const y=phase<0.25?174+phase/0.25*96:270;
 moving.setAttribute('transform',`translate(${x-740},${y-270})`);
 document.getElementById('movingLabel').textContent=phase===1?'completed':'completion lane';
 q0.textContent=phase>0?'—':'0';
 after.textContent=phase===1?'2':'—';
 progress.textContent=phase===1?'completedCourses: 1':'completedCourses: 0';
};
""")

slide(8, 'Release its <span class="hl">dependents</span>',
      "Finishing course 0 satisfies one prerequisite for each outgoing neighbor.",
      svg(arrow(225,252,588,132,id="release1") +
          arrow(225,288,588,408,id="release2") +
          node(160,270,0,"green",label="completed") +
          node(650,110,1,label="indegree: 1 → 0",id="dependent1") +
          node(650,430,2,label="indegree: 1 → 0",id="dependent2") +
          panel(0,535,936,110) +
          text(468,578,"indegree[dependent]--","orange",id="releaseStatus") +
          text(468,623,"Both neighbors become ready.","green",id="releaseOutcome") +
          '<circle id="token1" r="11" fill="#ffd166" visibility="hidden"/><circle id="token2" r="11" fill="#ffd166" visibility="hidden"/>',
          665),
      '<b>One prerequisite can unlock many courses.</b> Visit every dependent in relations.getOrDefault(...).',
      script="""
const starts=[[225,252],[225,288]],ends=[[588,132],[588,408]];
window.renderFrame=t=>{
 const p=t<0.8?0:t<3.2?(t-0.8)/2.4:t<5.4?1:0;
 for(let i=0;i<2;i++){
  const token=document.getElementById('token'+(i+1));
  token.setAttribute('visibility','visible');
  token.setAttribute('cx',starts[i][0]+p*(ends[i][0]-starts[i][0]));
  token.setAttribute('cy',starts[i][1]+p*(ends[i][1]-starts[i][1]));
  const group=document.getElementById('dependent'+(i+1));
  group.querySelector('circle').setAttribute('stroke',p===1?'#36d399':'#4dd8e6');
  group.querySelector('text.small').textContent=p===1?'indegree: 0 · READY':'indegree: 1 · WAIT';
 }
 document.getElementById('releaseStatus').textContent=p===1?'Each count drops by one.':'Satisfy the outgoing edges.';
 document.getElementById('releaseOutcome').textContent=p===1?'Enqueue courses 1 and 2.':'Course 0 has completed.';
};
""")

slide(9, 'Unlock only at <span class="hlg">zero</span>',
      "In a diamond, course 3 needs both course 1 and course 2.",
      svg(node(160,110,1,"green") + node(160,390,2,"green") +
          arrow(216,110,663,231,id="gate1") + arrow(216,390,663,269,id="gate2") +
          node(735,250,3,"orange",label="indegree: 2 → 1 → 0",id="gate") +
          text(380,133,"1 completes: 2 → 1","yellow",cls="small",id="gatefirst") +
          text(380,439,"2 completes: 1 → 0","green",cls="small",id="gatesecond") +
          panel(0,489,936,90) +
          text(468,544,"Wait at 1. Enqueue course 3 only at 0.","green",id="gateStatus") +
          '<circle id="gateToken" r="11" fill="#ffd166" visibility="hidden"/>',600),
      '<b>A first prerequisite is not enough.</b> Decrement the count, then test indegree[dependent] == 0.',
      script="""
window.renderFrame=t=>{
 let phase=t<0.8?0:t<2.6?1:t<4.4?2:t<5.4?3:0;
 let p=phase===1?(t-0.8)/1.8:phase===2?(t-2.6)/1.8:1;
 const token=document.getElementById('gateToken');
 token.setAttribute('visibility',phase===1||phase===2?'visible':'hidden');
 token.setAttribute('cx',216+p*(663-216));
 token.setAttribute('cy',(phase===2?390:110)+p*((phase===2?269:231)-(phase===2?390:110)));
 const count=phase<=1?2:phase===2?1:0;
 const gate=document.getElementById('gate');
 gate.querySelector('.small').textContent='indegree: '+count+(count===0?' · READY':' · WAIT');
 gate.querySelector('circle').setAttribute('stroke',count===0?'#36d399':'#ff9a3d');
 document.getElementById('gateStatus').textContent=count===2?'Course 3 still needs both prerequisites.':count===1?'One finished. Still blocked: do not enqueue.':'Both finished. Now enqueue course 3.';
};
""")

slide(10, 'Watch the <span class="hl">queue</span> evolve',
      "For [1,0], [2,0], [3,1], [3,2], one valid run is:",
      svg(diamond(completed=(0,1,2,3)) +
          panel(0,481,936,184) +
          text(30,523,"After finishing",color="muted",cls="small",anchor="start") +
          text(318,523,"Ready queue",color="muted",cls="small",anchor="start") +
          text(640,523,"Completed",color="muted",cls="small",anchor="start") +
          text(30,572,"0 → 1 → 2 → 3","green",anchor="start",id="runOrder") +
          text(318,572,"[1,2] → [2] → [3] → []",anchor="start",id="runQueue") +
          text(734,630,"4 / 4 · TRUE","green",id="runCount") +
          text(30,630,"Start queue: [0]",cls="small",anchor="start"),690),
      '<b>FIFO is enough.</b> A different valid ready-course order gives the same boolean result.',
      script="""
const states=[
 {done:[],counts:[0,1,1,2],queue:'[0]',order:'Start'},
 {done:[0],counts:[0,0,0,2],queue:'[1, 2]',order:'0'},
 {done:[0,1],counts:[0,0,0,1],queue:'[2]',order:'0 → 1'},
 {done:[0,1,2],counts:[0,0,0,0],queue:'[3]',order:'0 → 1 → 2'},
 {done:[0,1,2,3],counts:[0,0,0,0],queue:'[]',order:'0 → 1 → 2 → 3'}];
window.renderFrame=t=>{
 const index=t<0.8?0:t<1.8?1:t<2.8?2:t<3.8?3:t<5.4?4:0;
 const s=states[index];
 for(let n=0;n<4;n++){
  document.getElementById('node'+n).querySelector('circle').setAttribute('stroke',s.done.includes(n)?'#36d399':'#4dd8e6');
  const label=document.getElementById('count'+n);
  label.textContent=s.done.includes(n)?'DONE':'indegree = '+s.counts[n];
  label.style.fill=s.done.includes(n)?'#36d399':'#9aa7c7';
 }
 for(const [a,b] of [[0,1],[0,2],[1,3],[2,3]])
  document.getElementById('edge'+a+b).style.opacity=s.done.includes(a)?0.25:1;
 document.getElementById('runOrder').textContent=s.order;
 document.getElementById('runQueue').textContent=s.queue;
 document.getElementById('runCount').textContent=s.done.length+' / 4'+(index===4?' · TRUE':'');
};
""")

slide(11, 'A <span class="hl">cycle</span> never unlocks',
      "Every course in a directed cycle waits on another course in that cycle.",
      svg(node(170,160,0,"red",label="indegree 1") +
          node(720,160,1,"red",label="indegree 1") +
          arrow(223,142,662,142,"red",label="0 must finish first") +
          arrow(665,185,224,185,"red") +
          text(445,306,"0 → 1 → 0","red",cls="big") +
          panel(50,360,836,180,"No zero-indegree course exists.","red") +
          text(468,454,"readyCourses = [] · completedCourses = 0") +
          text(468,511,"0 != 2 → return false","red")),
      '<b>The same rule catches a 3-course cycle and a self-loop.</b> No special cycle-search branch is needed.')

slide(12, 'Not every <span class="hl">blocked</span> node cycles',
      "A cycle can also block a course downstream of it.",
      svg(node(110,150,0,"red") + node(390,150,1,"red") +
          arrow(165,132,335,132,"red") + arrow(335,180,165,180,"red") +
          arrow(445,150,715,150,"yellow") + node(775,150,2,"yellow") +
          text(250,258,"Cyclic core: 0 ↔ 1","red") +
          text(740,258,"2 is blocked, not cyclic","yellow",cls="small") +
          node(140,400,3,"green") + arrow(195,400,335,400,"green") +
          node(390,400,4,"green") + node(775,400,5,"green") +
          text(300,496,"Independent group completes.","green",cls="small") +
          text(775,496,"Isolated: completes","green",cls="small") +
          text(468,575,"Only 3 of 6 complete. The answer is still false.","red"),600),
      '<b>Leftover nodes mean a cycle exists somewhere.</b> They do not prove that every leftover node belongs to a cycle.')

slide(13, 'The <span class="hlg">count</span> is the proof',
      "A DAG is a directed acyclic graph: a graph with no directed cycle.",
      svg(panel(0,0,936,241,"No cycle → every remaining graph has a ready course.","green") +
          node(95,132,0,"green",radius=32) + arrow(138,132,236,132,"green") +
          node(280,132,1,"green",radius=32) + arrow(323,132,421,132,"green") +
          node(465,132,2,"green",radius=32) + arrow(508,132,606,132,"green") +
          text(770,142,"All removed","green") +
          text(468,211,"Repeatedly removing ready courses finishes every vertex.",cls="small") +
          panel(0,265,936,242,"Cycle → a nonempty locked remainder survives.","red") +
          node(200,387,0,"red",radius=32) + node(550,387,1,"red",radius=32) +
          arrow(243,370,507,370,"red") + arrow(507,407,243,407,"red") +
          text(780,399,"Stuck","red") +
          text(468,478,"Following an unfinished prerequisite must eventually loop.",cls="small") +
          text(468,561,"completedCourses == numCourses ⇔ no cycle","green"),585),
      '<b>Why “ready” must exist in a DAG:</b> otherwise, keep following prerequisites in a finite graph; some course repeats.')

BUILD_CODE = """Map<Integer, Set<Integer>> relations =
    new HashMap<>();
int[] indegree = new int[numCourses];

for (int[] prerequisite : prerequisites) {
    int course = prerequisite[0];
    int requiredCourse = prerequisite[1];
    if (relations.computeIfAbsent(
            requiredCourse, key -> new HashSet<>())
            .add(course)) {
        indegree[course]++;
    }
}"""
slide(14, 'Build the <span class="hl">Java graph</span>',
      "Source excerpt · CourseSchedule1.canFinish",
      f'<pre>{html.escape(BUILD_CODE)}</pre>' +
      '<div class="callout"><b>computeIfAbsent</b> creates a dependent set only when needed. <b>add</b> decides whether the edge is new.</div>',
      'The array starts at zero. A unique incoming edge adds one lock.')

LOOP_CODE = """Queue<Integer> readyCourses = new ArrayDeque<>();
for (int course = 0; course < numCourses; course++) {
    if (indegree[course] == 0)
        readyCourses.offer(course);
}
int completedCourses = 0;
while (!readyCourses.isEmpty()) {
    int course = readyCourses.poll();
    completedCourses++;
    for (int dependent : relations.getOrDefault(
            course, Collections.emptySet())) {
        indegree[dependent]--;
        if (indegree[dependent] == 0)
            readyCourses.offer(dependent);
    }
}
return completedCourses == numCourses;"""
slide(15, 'Run the <span class="hlg">Java loop</span>',
      "Same source logic · braces shortened for readability",
      f'<pre style="line-height:1.42">{html.escape(LOOP_CODE)}</pre>',
      '<b>emptySet()</b> makes a course with no dependents a safe no-op. The boolean does not return a course order.')

slide(16, 'Spend <span class="hlg">linear work</span>',
      "V = numCourses · P = input pairs · E = unique edges (E ≤ P)",
      svg(panel(0,0,936,155,"Build: inspect every pair once.","orange") +
          text(468,108,"P input pairs → E stored edges","orange",cls="big") +
          panel(0,178,936,190,"Traverse: each course and unique edge at most once.","cyan") +
          node(105,285,0,radius=31) + arrow(146,285,271,285) +
          node(315,285,1,radius=31) + arrow(356,285,481,285) +
          node(525,285,2,radius=31) + text(757,294,"V + E visits","cyan") +
          panel(0,390,936,170,"Store: graph + indegrees + queue.","green") +
          text(468,475,"O(V + E) auxiliary space","green",cls="big") +
          text(468,530,"O(V + P) is a valid upper bound.",cls="small")),
      '<b>Expected time: O(V + P).</b> HashMap / HashSet operations are assumed amortized constant-time; queue operations are too.')

slide(17, 'Test the <span class="hl">sharp edges</span>',
      "The source's 16 checks cover these input families.",
      svg(panel(0,0,936,183) +
          node(95,80,0,"green",radius=28) + text(230,91,"No edges: true","green",cls="small") +
          node(542,80,0,"red",radius=28) +
          '<path d="M525,53 C475,-10 610,-10 565,56" fill="none" stroke="#ff4d5e" stroke-width="4" marker-end="url(#red)"/>' +
          text(760,91,"Self-loop: false","red",cls="small") +
          text(468,151,"One course still counts. An isolated node is not a cycle.",cls="small"),200) +
      '<table><tr><th>Input family</th><th>What it checks</th><th>Result</th></tr>'
      '<tr><td>Single / no edges</td><td>All IDs enter the queue</td><td>true</td></tr>'
      '<tr><td>Chain / fan-out / fan-in / diamond</td><td>Release every edge; wait for all</td><td>true</td></tr>'
      '<tr><td>Self / 2-cycle / 3-cycle / tail</td><td>Queue stops before all finish</td><td>false</td></tr>'
      '<tr><td>Disconnected / unsorted / duplicate</td><td>Scan all IDs; honor edge direction</td><td>Cycle? false<br>Else true</td></tr></table>',
      '<b>Input contract:</b> nonnegative course count, non-null input, 2-item pairs, and IDs in range. This method does not validate malformed input.')

slide(18, 'Remember the <span class="hlg">unlock rule</span>',
      "Course Schedule I is cycle detection through safe removal.",
      svg(row_slots(8,62,["BUILD","COUNT","QUEUE","RELEASE","CHECK"],"Kahn's topological sort","green",width=173),155) +
      '<ul class="rules"><li><b>1.</b> Point each edge from prerequisite to course.</li>'
      '<li><b>2.</b> Count unique, unfinished prerequisites.</li>'
      '<li><b>3.</b> Queue every course whose count is zero.</li>'
      '<li><b>4.</b> Complete one; decrement its dependents.</li>'
      '<li><b>5.</b> All completed? True. Otherwise, a cycle exists.</li></ul>'
      '<div class="resource"><b>Resources</b><br>Implementation: CourseSchedule1.java · canFinish<br>Problem: leetcode.com/problems/course-schedule/<br>Algorithm: cp-algorithms.com/graph/topological-sort.html</div>'
      '<div class="analogy"><b>Save the pattern.</b> Follow @engineering.by.heart for visual algorithms, one idea at a time.</div>')


class CDP:
    """Small synchronous RFC 6455 client for a private local Chrome endpoint."""
    def __init__(self, url):
        from urllib.parse import urlsplit
        parsed = urlsplit(url)
        self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout=90)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (f"GET {parsed.path} HTTP/1.1\r\nHost: {parsed.hostname}:{parsed.port}\r\n"
                   f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                   "Sec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(request.encode())
        response = b""
        while not response.endswith(b"\r\n\r\n"):
            response += self.sock.recv(1)
        expected = base64.b64encode(hashlib.sha1((key+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest())
        if b" 101 " not in response or expected not in response:
            raise RuntimeError(f"WebSocket handshake failed: {response!r}")
        self.seq = 0

    def exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n-len(data))
            if not chunk:
                raise ConnectionError("Chrome closed the rendering connection")
            data += chunk
        return data

    def send(self, payload, opcode=1):
        mask = os.urandom(4)
        length = len(payload)
        prefix = bytes([0x80 | opcode])
        if length < 126:
            prefix += bytes([0x80 | length])
        elif length < 65536:
            prefix += bytes([0x80 | 126]) + struct.pack("!H", length)
        else:
            prefix += bytes([0x80 | 127]) + struct.pack("!Q", length)
        self.sock.sendall(prefix + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def receive(self):
        payloads = []
        while True:
            first, second = self.exact(2)
            opcode = first & 15
            length = second & 127
            if length == 126:
                length = struct.unpack("!H", self.exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self.exact(8))[0]
            mask = self.exact(4) if second & 128 else None
            payload = self.exact(length)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 8:
                raise ConnectionError("Chrome ended the WebSocket session")
            if opcode == 9:
                self.send(payload, 10)
                continue
            if opcode == 10:
                continue
            payloads.append(payload)
            if first & 128:
                return json.loads(b"".join(payloads))

    def call(self, method, params=None):
        self.seq += 1
        self.send(json.dumps({"id": self.seq, "method": method, "params": params or {}}).encode())
        while True:
            reply = self.receive()
            if reply.get("id") == self.seq:
                if "error" in reply:
                    raise RuntimeError(reply["error"])
                return reply.get("result", {})

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result["result"].get("value")

    def screenshot(self, path):
        shot = self.call("Page.captureScreenshot", {
            "format": "png", "captureBeyondViewport": True, "optimizeForSpeed": True,
            "clip": {"x": 0, "y": 0, "width": 1080, "height": 1350, "scale": 1},
        })
        Path(path).write_bytes(base64.b64decode(shot["data"]))


AUDIT = """
(()=>{
 const bad=[];
 const footer=document.querySelector('.footer').getBoundingClientRect();
 for(const el of document.querySelectorAll('h1,.sub,.note,.callout,.analogy,pre,td,th,.rules li,.resource,.kicker,.footer,svg text')){
  const r=el.getBoundingClientRect();
  if(r.left<71||r.right>1009||r.top<73||r.bottom>1281)
   bad.push({text:el.textContent,reason:'safe-area',rect:r.toJSON()});
  if(!el.closest('.footer')&&r.bottom>footer.top-18)
   bad.push({text:el.textContent,reason:'footer-overlap'});
  if(el.tagName==='PRE'&&el.scrollWidth>el.clientWidth)
   bad.push({text:el.textContent,reason:'code-overflow'});
  if(el.tagName==='text'){
   const box=el.getBBox(),view=el.closest('svg').viewBox.baseVal;
   if(box.x<0||box.y<0||box.x+box.width>view.width||box.y+box.height>view.height)
    bad.push({text:el.textContent,reason:'svg-overflow'});
  }
 }
 return bad;
})()
"""


def build(selected=None):
    if sorted(slides) != list(range(1,TOTAL+1)):
        raise ValueError("Missing slide content")
    expected = {f"{n}.png" for n in slides} | {f"{n}.gif" for n in slides if animations[n]}
    stale = {p.name for p in OUT.iterdir() if p.stem.isdigit() and p.suffix.lower() in {".png",".gif",".jpg",".jpeg",".webp"}} - expected
    if stale:
        raise RuntimeError(f"Reconcile stale numbered media before rendering: {sorted(stale)}")
    with tempfile.TemporaryDirectory(prefix="course-schedule-render-") as work:
        work = Path(work)
        profile = work / "chrome-profile"
        log = open(work / "chrome.log", "w")
        chrome = subprocess.Popen([CHROME,"--headless=new","--hide-scrollbars",
                                   "--disable-gpu-vsync","--disable-frame-rate-limit",
                                   "--run-all-compositor-stages-before-draw",
                                   "--no-first-run","--no-default-browser-check",
                                   "--disable-background-timer-throttling",
                                   "--disable-renderer-backgrounding",
                                   "--disable-backgrounding-occluded-windows",
                                   "--remote-debugging-port=0",f"--user-data-dir={profile}",
                                   "--window-size=1080,1350","about:blank"],stdout=log,stderr=log)
        cdp = None
        try:
            deadline = time.monotonic()+30
            active = profile / "DevToolsActivePort"
            while not active.exists():
                if chrome.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError("Dedicated Chrome session failed to start")
                time.sleep(0.1)
            port = active.read_text().splitlines()[0]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list",timeout=10) as response:
                targets = json.load(response)
            target = next(t for t in targets if t["type"] == "page")
            cdp = CDP(target["webSocketDebuggerUrl"])
            cdp.call("Page.enable")
            cdp.call("Emulation.setDeviceMetricsOverride",{"width":1080,"height":1350,"deviceScaleFactor":2,"mobile":False})
            for n in (selected or slides):
                page = work / f"{n}.html"
                page.write_text("<!doctype html><html><head>"+STYLE+"</head><body>"+slides[n]+
                                "<script>"+animations[n]+"</script></body></html>")
                cdp.call("Page.navigate",{"url":page.as_uri()})
                deadline = time.monotonic()+15
                while not cdp.evaluate(f"location.href === {json.dumps(page.as_uri())} && document.readyState === 'complete'"):
                    if time.monotonic()>deadline:
                        raise RuntimeError(f"Slide {n} did not load")
                    time.sleep(0.05)
                cdp.evaluate("document.fonts.ready")
                bad = cdp.evaluate(AUDIT)
                if bad:
                    raise RuntimeError(f"Slide {n} layout audit failed: {json.dumps(bad)}")
            print("Static layouts passed safe-area audit.",flush=True)
            for n in (selected or slides):
                page = work / f"{n}.html"
                page.write_text("<!doctype html><html><head>"+STYLE+"</head><body>"+slides[n]+
                                "<script>"+animations[n]+"</script></body></html>")
                cdp.call("Emulation.setDeviceMetricsOverride",{"width":1080,"height":1350,"deviceScaleFactor":2,"mobile":False})
                cdp.call("Page.navigate",{"url":page.as_uri()})
                deadline = time.monotonic()+15
                while not cdp.evaluate(f"location.href === {json.dumps(page.as_uri())} && document.readyState === 'complete'"):
                    if time.monotonic()>deadline:
                        raise RuntimeError(f"Slide {n} did not load")
                    time.sleep(0.05)
                cdp.evaluate("document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))")
                bad = cdp.evaluate(AUDIT)
                if bad:
                    raise RuntimeError(f"Slide {n} layout audit failed: {json.dumps(bad)}")
                cdp.screenshot(OUT / f"{n}.png")
                with Image.open(OUT / f"{n}.png") as image:
                    assert image.size == (2160,2700)
                print(f"PNG {n:02d}/{TOTAL}",flush=True)
                if animations[n]:
                    cdp.call("Emulation.setDeviceMetricsOverride",{"width":1080,"height":1350,"deviceScaleFactor":1,"mobile":False})
                    animation_url = page.as_uri()+"?animation=1"
                    cdp.call("Page.navigate",{"url":animation_url})
                    deadline = time.monotonic()+15
                    while not cdp.evaluate(f"location.href === {json.dumps(animation_url)} && document.readyState === 'complete' && typeof window.renderFrame === 'function'"):
                        if time.monotonic()>deadline:
                            raise RuntimeError(f"Animation {n} did not load")
                        time.sleep(0.05)
                    cdp.evaluate("document.fonts.ready")
                    cdp.evaluate("""
const svg=document.querySelector('svg');
const timing=document.createElementNS('http://www.w3.org/2000/svg','text');
timing.setAttribute('x','908'); timing.setAttribute('y','28');
timing.setAttribute('class','small'); timing.setAttribute('text-anchor','end');
timing.textContent='Illustrative steps · 6-second loop';
svg.appendChild(timing);
""")
                    frames = work / f"frames-{n}"
                    frames.mkdir()
                    previous_scene = None
                    for frame in range(DURATION*FPS):
                        cdp.evaluate(f"window.renderFrame({frame/FPS})")
                        bad = cdp.evaluate(AUDIT)
                        if bad:
                            raise RuntimeError(f"Animation {n} frame {frame}: {bad}")
                        scene = cdp.evaluate("document.body.innerHTML")
                        frame_path = frames / f"{frame:04d}.png"
                        if scene == previous_scene:
                            shutil.copyfile(frames / f"{frame-1:04d}.png", frame_path)
                        else:
                            cdp.screenshot(frame_path)
                        previous_scene = scene
                        if frame % 20 == 0:
                            print(f"GIF {n:02d}: captured frame {frame}/{DURATION*FPS}",flush=True)
                    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),
                                    "-i",str(frames / "%04d.png"),"-filter_complex",
                                    "[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a",
                                    "-loop","0",str(OUT / f"{n}.gif")],check=True)
                    with Image.open(OUT / f"{n}.gif") as gif:
                        assert gif.size == (1080,1350) and gif.is_animated and gif.info.get("loop") == 0
                        total_ms = 0
                        for frame in range(gif.n_frames):
                            gif.seek(frame)
                            delay = gif.info.get("duration",0)
                            assert delay > 0
                            total_ms += delay
                        assert total_ms == DURATION*1000
                    print(f"GIF {n:02d}: {DURATION}s, {FPS} fps",flush=True)
        except Exception:
            log.flush()
            print((work / "chrome.log").read_text()[-4000:],flush=True)
            raise
        finally:
            if cdp:
                cdp.sock.close()
            if chrome.poll() is None:
                chrome.terminate()
                try:
                    chrome.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    chrome.kill()
                    chrome.wait(timeout=10)
            log.close()
    if selected is None:
        actual_pngs = {p.name for p in OUT.glob("*.png")}
        assert actual_pngs == {f"{n}.png" for n in slides}
        print(f"DONE: {TOTAL} PNGs + {sum(bool(s) for s in animations.values())} GIFs",flush=True)


if __name__ == "__main__":
    build()

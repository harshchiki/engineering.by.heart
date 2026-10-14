#!/usr/bin/env python3
"""Verify PNG headers and decoded GIFs using the standard library and FFmpeg."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

OUT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("review_dir", type=Path)
args = parser.parse_args()
args.review_dir.mkdir(parents=True, exist_ok=True)
expected = {f"{n}.png" for n in range(1, 21)}
assert {p.name for p in OUT.glob("*.png")} == expected
assert {p.name for p in OUT.glob("*.gif")} == {"7.gif", "11.gif", "12.gif"}
for n in range(1, 21):
    header = (OUT / f"{n}.png").read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (2160, 2700)

def ffmpeg(arguments):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arguments],
                   check=True, timeout=120)

for group in range(4):
    numbers = list(range(group*5+1, group*5+6))
    inputs = [arg for n in numbers for arg in ("-i", str(OUT / f"{n}.png"))]
    filters = ";".join(f"[{i}:v]scale=360:450[s{i}]" for i in range(5))
    filters += ";" + "".join(f"[s{i}]" for i in range(5))
    filters += "xstack=inputs=5:layout=0_0|360_0|720_0|0_450|360_450:fill=0x0a1020[out]"
    ffmpeg([*inputs, "-filter_complex", filters, "-map", "[out]", "-frames:v", "1",
            str(args.review_dir / f"slides-{group+1}.png")])

results = []
for n in (7, 11, 12):
    file = OUT / f"{n}.gif"
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_frames",
                            "-of", "json", str(file)], check=True, capture_output=True, text=True)
    info = json.loads(probe.stdout)
    stream = info["streams"][0]
    assert (stream["width"], stream["height"]) == (1080, 1350)
    frames = info["frames"]
    assert len(frames) > 10
    durations = [float(f.get("duration_time", f.get("pkt_duration_time", "0"))) for f in frames]
    assert all(d > 0 for d in durations)
    duration = round(sum(durations)*1000)
    assert duration == 6000, duration
    data = file.read_bytes()
    assert b"NETSCAPE2.0\x03\x01\x00\x00" in data
    hashes = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i",
                             str(file), "-f", "framemd5", "-"], check=True,
                            capture_output=True, text=True, timeout=120)
    distinct = {line.rsplit(",", 1)[-1].strip() for line in hashes.stdout.splitlines()
                if line and not line.startswith("#")}
    assert len(distinct) > 10
    ffmpeg(["-i", str(file), "-vf", "fps=1,scale=270:338,tile=3x2",
            "-frames:v", "1", str(args.review_dir / f"animation-{n}.png")])
    results.append(dict(slide=n, durationMs=duration, frames=len(frames),
                        distinctDecodedFrames=len(distinct), size=[1080, 1350]))
report = dict(pngCount=20, pngSize=[2160, 2700], gifs=results, logicalSlides=20,
              order=[f"{n}.png" for n in range(1, 21)])
(OUT / "media-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

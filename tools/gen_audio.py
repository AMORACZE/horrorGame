#!/usr/bin/env python3
"""Generate every sound id in docs/ARCHITECTURE.md section 8 into audio/sounds/.

    python3 tools/gen_audio.py                 # everything
    python3 tools/gen_audio.py fridge_hum door_close footstep_wood   # just these ids
    python3 tools/gen_audio.py --list          # print the registry

Layout: audio/sounds/<id>/<id>_NN.wav|ogg  (one folder per id; every audio file in
the folder is a variant). The Godot side (audio/sound_library.gd) discovers the
files in each folder, so replacing a sound with a real recording is: delete the
generated files in its folder, drop yours in, re-import.

Deterministic: every variant is seeded from crc32("<id>:<variant>") ^ SEED.
Requires numpy + scipy; ffmpeg (libvorbis) for the .ogg files.
"""
from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_gen import dsp, foley, loops, distant  # noqa: E402

SEED = 1993_08_26
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "audio", "sounds")
OGG_QUALITY = 5  # libvorbis -q (about 160 kbps stereo); transparent for these textures


@dataclass
class Spec:
    id: str
    fn: Callable
    variants: int = 1
    loop: bool = False
    stereo: bool = False
    target: float = -20.0          # LUFS-ish: momentary-max for one-shots, integrated for loops
    fmt: str = "wav"               # wav | ogg
    peak: float = -1.0             # dBFS ceiling
    vary_db: float = 1.0           # per-variant level spread for one-shots (natural variation)
    notes: str = ""
    extra: dict = field(default_factory=dict)


def _fs(surface):
    return lambda rng, v: foley.footstep(surface, rng, v)


def _loop(fn):
    return lambda rng, v: fn(rng)


SPECS: list[Spec] = []


def add(*a, **k):
    SPECS.append(Spec(*a, **k))


# --- footsteps (rug plays as carpet, see audio_manager) ---------------------------
for s in ("wood", "carpet", "linoleum", "tile", "concrete"):
    add(f"footstep_{s}", _fs(s), 6, target={"carpet": -26.0}.get(s, -21.0), vary_db=1.5)

# --- interaction --------------------------------------------------------------------
add("door_open", foley.door_open, 4, target=-22.0)
add("door_close", foley.door_close, 4, target=-16.0)
add("door_locked", foley.door_locked, 4, target=-19.0)
add("door_creak", foley.door_creak, 4, target=-21.0)
add("drawer_open", foley.drawer_open, 4, target=-21.0)
add("drawer_close", foley.drawer_close, 4, target=-19.0)
add("cabinet_open", foley.cabinet_open, 4, target=-23.0)
add("cabinet_close", foley.cabinet_close, 4, target=-19.0)
add("switch_on", foley.switch_on, 4, target=-24.0)
add("switch_off", foley.switch_off, 4, target=-24.0)
add("lamp_click", foley.lamp_click, 4, target=-25.0)
add("button_press", foley.button_press, 4, target=-25.0)
add("pickup", foley.pickup, 5, target=-25.0)
add("putdown", foley.putdown, 5, target=-22.0)
add("paper_rustle", foley.paper_rustle, 5, target=-24.0)
add("tv_on", foley.tv_on, 3, target=-21.0)
add("tv_off", foley.tv_off, 3, target=-23.0)
add("phone_pickup", foley.phone_pickup, 4, target=-23.0)
add("phone_hangup", foley.phone_hangup, 4, target=-20.0)
add("fridge_open", foley.fridge_open, 4, target=-22.0)
add("fridge_close", foley.fridge_close, 4, target=-18.0)
add("tape_insert", foley.tape_insert, 3, target=-22.0)
add("glass_clink", foley.glass_clink, 4, target=-23.0)
add("book_slide", foley.book_slide, 4, target=-23.0)
add("cloth_rustle", foley.cloth_rustle, 5, target=-27.0)
add("thud_soft", foley.thud_soft, 4, target=-19.0)
add("window_rattle", foley.window_rattle, 4, target=-21.0)
add("faucet_squeak", foley.faucet_squeak, 4, target=-23.0)

# --- loops ------------------------------------------------------------------------
add("room_tone", _loop(loops.room_tone), loop=True, stereo=True, target=-30.0, fmt="ogg")
add("outside_afternoon", _loop(loops.outside_afternoon), loop=True, stereo=True, target=-26.0, fmt="ogg")
add("wind_light", _loop(loops.wind_light), loop=True, stereo=True, target=-28.0, fmt="ogg")
add("fridge_hum", _loop(loops.fridge_hum), loop=True, target=-24.0)
add("clock_tick", _loop(loops.clock_tick), loop=True, target=-30.0)
add("tv_static", _loop(loops.tv_static), loop=True, target=-24.0)
add("light_buzz", _loop(loops.light_buzz), loop=True, target=-26.0)
add("fly_buzz", _loop(loops.fly_buzz), loop=True, target=-28.0, fmt="ogg")
add("phone_dial_tone", _loop(loops.phone_dial_tone), loop=True, target=-24.0)
add("faucet_run", _loop(loops.faucet_run), loop=True, target=-23.0)
add("camcorder_motor", _loop(loops.camcorder_motor), loop=True, target=-30.0)
add("camcorder_zoom", _loop(loops.camcorder_zoom), loop=True, target=-26.0)
add("tape_hiss", _loop(loops.tape_hiss), loop=True, target=-30.0)

# --- random ambient one-shots -----------------------------------------------------
add("house_settle", distant.house_settle, 6, target=-22.0, vary_db=3.0)
add("distant_dog", distant.distant_dog, 4, target=-26.0, fmt="ogg", vary_db=2.0)
add("distant_car", distant.distant_car, 4, target=-26.0, fmt="ogg", vary_db=2.0)
add("distant_mower", distant.distant_mower, 4, target=-27.0, fmt="ogg", vary_db=2.0)

# --- UI ---------------------------------------------------------------------------
add("ui_tick", foley.ui_tick, 3, target=-30.0, vary_db=0.5)
add("ui_open", foley.ui_open, 3, target=-27.0, vary_db=0.5)
add("ui_close", foley.ui_close, 3, target=-28.0, vary_db=0.5)

BY_ID = {s.id: s for s in SPECS}


# --------------------------------------------------------------------------- finishing

def finish_oneshot(x: np.ndarray, spec: Spec, rng: np.random.Generator) -> np.ndarray:
    x = dsp.highpass(x, 20.0, 2)  # causal: no pre-ringing before the onset
    # trim trailing near-silence (relative to peak), keep a short fade
    pk = np.max(np.abs(x)) + 1e-12
    env = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    above = np.nonzero(env > pk * dsp.db(-66))[0]
    end = min(len(x), (above[-1] if len(above) else len(x)) + dsp.samples(0.03))
    x = x[:end]
    x = dsp.fade(x, 0.0008, min(0.03, dsp.secs(len(x)) * 0.2))
    target = spec.target + rng.uniform(-spec.vary_db, spec.vary_db) * 0.5
    # reach the loudness target, let a look-ahead limiter shave the sharpest
    # transients (as a recording chain would), then hard-cap whatever is left
    x = dsp.normalize(x, target, "momentary_max", peak_ceiling_db=60.0)
    x = dsp.limit(x, spec.peak - 0.3, max_gr_db=spec.extra.get("max_gr", 6.0))
    for _ in range(3):  # limiting lowers loudness a little: one more nudge
        L = dsp.loudness(x)["momentary_max"]
        if abs(L - target) < 0.3:
            break
        x = dsp.limit(x * dsp.db(min(target - L, 3.0)), spec.peak - 0.3, max_gr_db=3.0)
    pk = np.max(np.abs(x))
    if pk > dsp.db(spec.peak):
        x *= dsp.db(spec.peak) / pk
    return x


def finish_loop(x: np.ndarray, spec: Spec) -> np.ndarray:
    x = dsp.highpass_c(x - np.mean(x, axis=0), 18.0, 2)  # circular: DC and sub-sonics out, seam intact
    return dsp.normalize(x, spec.target, "integrated", spec.peak)


def to_int16(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    # TPDF dither; noise is periodic-safe (independent per sample) and ~-96 dBFS
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768.0
    return np.clip(np.round((x + d) * 32767.0), -32768, 32767).astype("<i2")


GUARD = 4  # samples copied from the loop start after the loop end (interpolation guard)


def write_wav(path: str, data: np.ndarray, loop: bool) -> None:
    ch = 1 if data.ndim == 1 else data.shape[1]
    frames = len(data)
    if loop:
        # Godot treats the 'smpl' end as exclusive and resamples across the seam,
        # so store end = N and follow it with copies of the first samples.
        data = np.concatenate([data, data[:GUARD]])
    raw = data.tobytes()
    fmt = struct.pack("<HHIIHH", 1, ch, dsp.SR, dsp.SR * ch * 2, ch * 2, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    chunks += b"data" + struct.pack("<I", len(raw)) + raw
    if len(raw) % 2:
        chunks += b"\0"
    if loop:
        # 'smpl' chunk: one forward loop over the whole file (end is inclusive)
        smpl = struct.pack("<9I", 0, 0, int(1e9 / dsp.SR), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, frames, 0, 0)
        chunks += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


def write_ogg(path: str, data: np.ndarray) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "x.wav")
        write_wav(tmp, data, False)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", tmp,
                        "-c:a", "libvorbis", "-q:a", str(OGG_QUALITY),
                        # reproducible output: fixed stream serial, no encoder/date tags
                        "-fflags", "+bitexact", "-flags:a", "+bitexact", "-serial_offset", "1993",
                        "-map_metadata", "-1", path], check=True)


def render(spec_id: str) -> list[str]:
    spec = BY_ID[spec_id]
    folder = os.path.join(OUT, spec.id)
    os.makedirs(folder, exist_ok=True)
    # remove stale generated variants (generated files carry the <id>_NN prefix)
    for f in os.listdir(folder):
        if f.startswith(spec.id + "_") and f.split(".")[-1] in ("wav", "ogg"):
            os.remove(os.path.join(folder, f))
    written = []
    for v in range(spec.variants):
        seed = (zlib.crc32(f"{spec.id}:{v}".encode()) ^ SEED) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        x = np.asarray(spec.fn(rng, v), dtype=np.float64)
        if spec.stereo and x.ndim == 1:
            x = np.stack([x, x], axis=1)
        if not spec.stereo and x.ndim == 2:
            x = x.mean(axis=1)
        y = finish_loop(x, spec) if spec.loop else finish_oneshot(x, spec, rng)
        pcm = to_int16(y, rng)
        name = f"{spec.id}_{v + 1:02d}.{spec.fmt}"
        path = os.path.join(folder, name)
        if spec.fmt == "ogg":
            write_ogg(path, pcm)
        else:
            write_wav(path, pcm, spec.loop)
        written.append(os.path.relpath(path, ROOT))
    return written


def write_import_hints(spec: Spec) -> None:
    """Pre-seed .import files for looping OGGs so Godot imports them with loop=true.

    Godot keeps [params] from an existing .import file and fills in the rest
    (uid, dest files) on import. WAV loops carry a 'smpl' chunk instead, which
    the WAV importer's default loop mode ("Detect From WAV") picks up.
    """
    if not (spec.loop and spec.fmt == "ogg"):
        return
    folder = os.path.join(OUT, spec.id)
    for f in os.listdir(folder):
        if not f.endswith(".ogg"):
            continue
        imp = os.path.join(folder, f + ".import")
        text = open(imp).read() if os.path.exists(imp) else ""
        if "loop=true" in text:
            continue
        if "[params]" in text:
            lines = [ln for ln in text.splitlines() if not ln.startswith("loop=")]
            i = lines.index("[params]")
            lines.insert(i + 1, "loop=true")
            text = "\n".join(lines) + "\n"
        else:
            text = ("[remap]\n\nimporter=\"oggvorbisstr\"\ntype=\"AudioStreamOggVorbis\"\n\n"
                    "[params]\n\nloop=true\nloop_offset=0.0\nbpm=0.0\nbeat_count=0\nbar_beats=4\n")
        with open(imp, "w") as fh:
            fh.write(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="only these ids (default: all)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=2, help="worker processes (default 2)")
    ap.add_argument("--no-analyze", action="store_true")
    args = ap.parse_args()
    if args.list:
        for s in SPECS:
            print(f"{s.id:20s} variants={s.variants} loop={s.loop} stereo={s.stereo} fmt={s.fmt} target={s.target}")
        return 0
    if not shutil.which("ffmpeg"):
        print("ffmpeg not found (needed for .ogg)", file=sys.stderr)
        return 1
    ids = args.ids or [s.id for s in SPECS]
    unknown = [i for i in ids if i not in BY_ID]
    if unknown:
        print("unknown ids:", unknown, file=sys.stderr)
        return 1
    t0 = time.time()
    # longest jobs first for better packing
    ids.sort(key=lambda i: -(BY_ID[i].loop * 10 + BY_ID[i].variants))
    with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        for sid, files in zip(ids, ex.map(render, ids)):
            print(f"  {sid:20s} {len(files)} file(s)")
    for i in ids:
        write_import_hints(BY_ID[i])
    print(f"generated {len(ids)} ids in {time.time() - t0:.1f}s")
    if not args.no_analyze:
        sys.path.insert(0, os.path.join(ROOT, "tests", "audio"))
        import analyze  # noqa: E402
        return analyze.main([os.path.join(OUT, i) for i in ids])
    return 0


if __name__ == "__main__":
    sys.exit(main())

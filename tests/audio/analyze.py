#!/usr/bin/env python3
"""Objective checks for the generated (or replaced) sound files.

    python3 tests/audio/analyze.py                      # every folder in audio/sounds
    python3 tests/audio/analyze.py audio/sounds/fridge_hum --png /tmp/specs

Per file: duration, channels, peak dBFS, LUFS-ish integrated and momentary-max
loudness (K-weighted, ungated), spectral centroid, DC offset, edge levels and,
for loops, the seam discontinuity:

  seam_jump  = |x[0] - x[-1]| / p99(|x[n+1] - x[n]|)      (< ~1 is inaudible)
  seam_flux  = HF energy in a window across the seam / median HF energy of
               the same window size elsewhere              (relative to the 95th percentile; < ~3 is fine)

Exit code is non-zero if any hard rule fails: clipping, DC > 0.002 (loops) / 0.01 (one-shots), a one-shot
starting/ending above -50 dBFS, a loop with seam_jump > 2 or seam_flux > 4.
OGG files are decoded with ffmpeg exactly as encoded, so seams are checked
after the lossy codec too.
"""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from audio_gen import dsp  # noqa: E402

LOOP_IDS = {"room_tone", "outside_afternoon", "wind_light", "fridge_hum", "clock_tick", "tv_static",
            "light_buzz", "fly_buzz", "phone_dial_tone", "faucet_run", "camcorder_motor",
            "camcorder_zoom", "tape_hiss"}


def load(path: str) -> tuple[np.ndarray, int]:
    if path.endswith(".wav"):
        import warnings
        from scipy.io import wavfile
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # the 'smpl' loop chunk is unknown to scipy
            sr, d = wavfile.read(path)
    else:
        raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-f", "s16le",
                              "-acodec", "pcm_s16le", "-"], capture_output=True, check=True).stdout
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=channels,sample_rate",
                               "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout
        sr_s, ch_s = info.strip().split("\n")[0].split(",")
        sr, ch = int(sr_s), int(ch_s)
        d = np.frombuffer(raw, dtype="<i2")
        if ch > 1:
            d = d.reshape(-1, ch)
    x = d.astype(np.float64) / 32768.0
    if path.endswith(".wav") and len(x) > 64 and np.array_equal(x[-4:], x[:4]):
        x = x[:-4]  # loop guard samples written by gen_audio.py (not part of the loop)
    return x, sr


def seam(x: np.ndarray) -> tuple[float, float]:
    m = x if x.ndim == 1 else x.mean(axis=1)
    diff = np.abs(np.diff(m))
    p99 = np.percentile(diff, 99) + 1e-9
    jump = abs(m[0] - m[-1]) / p99
    hf = np.diff(np.concatenate([m[-1:], m])) ** 2  # circular first difference
    w = 512
    c = np.cumsum(np.concatenate([[0.0], np.concatenate([hf, hf[:w]])]))
    win = c[w:w + len(hf)] - c[:len(hf)]
    seam_val = win[len(hf) - w // 2]  # window centred on the seam
    flux = seam_val / (np.percentile(win, 95) + 1e-12)
    return float(jump), float(flux)


def centroid(x: np.ndarray, sr: int) -> float:
    m = x if x.ndim == 1 else x.mean(axis=1)
    n = min(len(m), sr * 20)
    X = np.abs(np.fft.rfft(m[:n] * np.hanning(n)))
    f = np.fft.rfftfreq(n, 1 / sr)
    return float(np.sum(f * X) / (np.sum(X) + 1e-12))


def spectrogram_png(x: np.ndarray, sr: int, path: str, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    m = x if x.ndim == 1 else x.mean(axis=1)
    fig, ax = plt.subplots(3, 1, figsize=(10, 7), gridspec_kw={"height_ratios": [1, 3, 2]})
    t = np.arange(len(m)) / sr
    ax[0].plot(t, m, lw=0.4)
    ax[0].set_xlim(0, t[-1])
    ax[0].set_title(title)
    nfft = 1024 if len(m) > sr else 256
    Pxx, _, _, _ = ax[1].specgram(m + 1e-9, NFFT=nfft, Fs=sr, noverlap=nfft * 3 // 4, cmap="magma", scale="dB")
    ax[1].cla()
    top = 10 * np.log10(Pxx.max() + 1e-20)
    ax[1].specgram(m + 1e-9, NFFT=nfft, Fs=sr, noverlap=nfft * 3 // 4, cmap="magma", scale="dB",
                   vmin=top - 80, vmax=top)
    ax[1].set_ylim(0, 12000)
    nfft = 8192 if len(m) > 4 * sr else 2048
    Pxx, _, _, _ = ax[2].specgram(m + 1e-9, NFFT=nfft, Fs=sr, noverlap=nfft * 3 // 4, cmap="magma", scale="dB")
    top = 10 * np.log10(Pxx.max() + 1e-20)
    ax[2].cla()
    ax[2].specgram(m + 1e-9, NFFT=nfft, Fs=sr, noverlap=nfft * 3 // 4, cmap="magma", scale="dB",
                   vmin=top - 70, vmax=top)
    ax[2].set_ylim(0, 1500)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def analyze_file(path: str, png_dir: str | None) -> tuple[dict, list[str]]:
    x, sr = load(path)
    sid = os.path.basename(os.path.dirname(path))
    is_loop = sid in LOOP_IDS
    pk = float(np.max(np.abs(x)))
    L = dsp.loudness(x)
    dc = float(np.max(np.abs(np.mean(x, axis=0))))
    m = x if x.ndim == 1 else np.max(np.abs(x), axis=1)
    edge_in = dsp.to_db(float(np.max(np.abs(m[:16]))))
    edge_out = dsp.to_db(float(np.max(np.abs(m[-16:]))))
    r = {"file": os.path.relpath(path, ROOT), "dur": len(x) / sr, "ch": 1 if x.ndim == 1 else x.shape[1],
         "peak": dsp.to_db(pk), "lufs_i": L["integrated"], "lufs_m": L["momentary_max"],
         "centroid": centroid(x, sr), "dc": dc, "edge_in": edge_in, "edge_out": edge_out,
         "loop": is_loop, "seam_jump": float("nan"), "seam_flux": float("nan")}
    errs = []
    if pk >= 0.999:
        errs.append("clipping")
    # a short low thump legitimately has a non-zero mean; a real offset shows on loops
    if dc > (0.002 if is_loop else 0.01):
        errs.append(f"DC {dc:.4f}")
    if is_loop:
        j, fl = seam(x)
        r["seam_jump"], r["seam_flux"] = j, fl
        if j > 2.0 or fl > 4.0:
            errs.append(f"seam jump={j:.2f} flux={fl:.2f}")
    else:
        if edge_in > -50 or edge_out > -50:
            errs.append(f"edge click in={edge_in:.0f} out={edge_out:.0f} dBFS")
    if sr != 44100:
        errs.append(f"sample rate {sr}")
    if png_dir:
        os.makedirs(png_dir, exist_ok=True)
        spectrogram_png(x, sr, os.path.join(png_dir, os.path.basename(path) + ".png"), r["file"])
    return r, errs


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    png = None
    if "--png" in argv:
        i = argv.index("--png")
        png = argv[i + 1]
        del argv[i:i + 2]
    base = os.path.join(ROOT, "audio", "sounds")
    folders = argv or sorted(os.path.join(base, d) for d in os.listdir(base))
    files = []
    for f in folders:
        if os.path.isdir(f):
            files += sorted(os.path.join(f, n) for n in os.listdir(f) if n.endswith((".wav", ".ogg")))
        elif f.endswith((".wav", ".ogg")):
            files.append(f)
    hdr = f"{'file':52s} {'dur':>6s} {'ch':>2s} {'peak':>6s} {'LUFSi':>6s} {'LUFSm':>6s} {'cent':>6s} {'seamJ':>6s} {'seamF':>6s}"
    print(hdr)
    print("-" * len(hdr))
    failures = 0
    total = 0
    for p in files:
        r, errs = analyze_file(p, png)
        total += os.path.getsize(p)
        sj = f"{r['seam_jump']:6.2f}" if r["loop"] else "     -"
        sf = f"{r['seam_flux']:6.2f}" if r["loop"] else "     -"
        print(f"{r['file'][len('audio/sounds/'):]:52s} {r['dur']:6.2f} {r['ch']:2d} {r['peak']:6.1f} "
              f"{r['lufs_i']:6.1f} {r['lufs_m']:6.1f} {r['centroid']:6.0f} {sj} {sf}"
              + ("   FAIL: " + "; ".join(errs) if errs else ""))
        failures += bool(errs)
    print(f"\n{len(files)} files, {total / 1e6:.2f} MB, {failures} with problems")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

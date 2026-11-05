"""Procedural sound effects for the Godot game (numpy only), written as 16-bit mono WAV.

    python sfx_gen.py [--out ../../game/assets/sfx]

Loops (*_loop.wav) are periodic over their length (noise is shaped in the frequency domain of the
whole buffer, tones have whole numbers of cycles), so they repeat without clicks."""
import argparse
import os
import wave

import numpy as np

SR = 44100
rng = np.random.default_rng(1975)


def t_(dur):
    return np.arange(int(SR * dur)) / SR


def periodic_noise(dur, lo=20, hi=20000, tilt=0.0, seed=None):
    """Band-limited noise that loops seamlessly (FFT shaping of the whole buffer)."""
    r = np.random.default_rng(seed) if seed is not None else rng
    n = int(SR * dur)
    spec = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    g = ((f >= lo) & (f <= hi)).astype(float) * np.where(f > 0, (np.maximum(f, 1) / 1000.0) ** tilt, 0)
    x = np.fft.irfft(spec * g, n)
    return x / (np.abs(x).max() + 1e-9)


def noise(dur, lo=20, hi=20000, tilt=0.0):
    return periodic_noise(dur, lo, hi, tilt)


def bandpass(x, lo, hi):
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(spec, n)


def env(n, a=0.005, d=0.1, s=None):
    """Attack / exponential decay envelope over n samples."""
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(t - a, 0) / max(d, 1e-4))
    return e


def fade(x, fi=0.005, fo=0.02):
    n = len(x)
    a, b = int(SR * fi), int(SR * fo)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def norm(x, peak=0.9):
    return x / (np.abs(x).max() + 1e-9) * peak


def click(dur=0.03, f=3000, d=0.004):
    t = t_(dur)
    x = np.sin(2 * np.pi * f * t) * env(len(t), 0.0003, d) + noise(dur, 1500, 12000) * env(len(t), 0.0002, d * 0.7)
    return fade(x, 0, 0.005)


def thud(dur=0.35, f=70, d=0.08):
    t = t_(dur)
    sweep = f * (1 + 0.8 * np.exp(-t / 0.02))
    x = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * env(len(t), 0.001, d)
    x += 0.4 * bandpass(noise(dur), 60, 600) * env(len(t), 0.001, d * 0.5)
    return fade(x, 0, 0.02)


def creak(dur=1.1, f0=180, f1=320, rough=0.6, seed=1):
    """Hinge creak: a stick-slip pulse train with a wandering pitch, through two resonances."""
    r = np.random.default_rng(seed)
    t = t_(dur)
    wander = np.cumsum(r.standard_normal(len(t))) / SR
    wander = (wander - wander.mean()) / (np.abs(wander).max() + 1e-9)
    f = f0 + (f1 - f0) * (0.5 + 0.5 * np.sin(np.pi * t / dur * 1.3)) + 40 * wander
    ph = np.cumsum(f) / SR
    pulses = (np.sin(2 * np.pi * ph) > 0.92).astype(float) * (0.6 + 0.4 * r.random(len(t)))
    x = bandpass(pulses, 400, 2600) + 0.5 * bandpass(pulses, 2600, 6000)
    x += rough * 0.2 * bandpass(r.standard_normal(len(t)), 1200, 4000)
    am = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7 * (0.7 + 0.3 * np.sin(2 * np.pi * 3.1 * t))
    return fade(x * am, 0.02, 0.08)


def write(path, x, peak=0.9):
    x = norm(np.asarray(x, float), peak)
    y = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def make_all(out):
    os.makedirs(out, exist_ok=True)
    W = lambda name, x, peak=0.9: write(os.path.join(out, name + ".wav"), x, peak)

    # --- electric wheelchair ---------------------------------------------------------------
    dur = 2.0
    t = t_(dur)
    motor = np.zeros_like(t)
    for f, a in ((150, 0.5), (300, 0.35), (450, 0.2), (1200, 0.08), (2400, 0.05)):   # whole cycles in 2 s
        motor += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6))
    motor *= 1 + 0.08 * np.sin(2 * np.pi * 7 * t)
    motor += 0.18 * periodic_noise(dur, 900, 3500, -0.5, seed=11)
    W("motor_loop", motor, 0.7)
    roll = periodic_noise(dur, 30, 900, -1.2, seed=12)
    roll *= 1 + 0.25 * np.sin(2 * np.pi * 3 * t)                      # tyre lugs / floor joints
    roll += 0.25 * periodic_noise(dur, 900, 3000, -1.0, seed=13)
    W("wheels_loop", roll, 0.7)
    W("brake_release", np.concatenate([click(0.04, 1800, 0.006) * 0.8, np.zeros(int(SR * 0.05)),
                                       click(0.05, 900, 0.01)]))
    W("brake_engage", np.concatenate([click(0.05, 1100, 0.012), thud(0.12, 120, 0.02) * 0.3]))
    W("bump", thud(0.4, 75, 0.09) + 0.3 * np.pad(click(0.03, 2500, 0.004), (0, int(SR * 0.37))))
    tt = t_(0.5)
    horn = (np.sign(np.sin(2 * np.pi * 620 * tt)) * 0.5 + np.sin(2 * np.pi * 930 * tt)) * env(len(tt), 0.01, 0.6)
    W("horn", fade(bandpass(horn, 300, 4000), 0.01, 0.05), 0.6)

    # --- doors -----------------------------------------------------------------------------
    latch = click(0.06, 2200, 0.008) + 0.6 * np.pad(click(0.04, 1400, 0.01), (int(SR * 0.02), 0))[:int(SR * 0.06)]
    W("door_open_wood", np.concatenate([latch, creak(1.2, 160, 300, seed=2) * 0.7]))
    W("door_open_wood2", np.concatenate([latch, creak(0.9, 230, 420, seed=3) * 0.6]))
    close = np.concatenate([creak(0.35, 260, 200, seed=4) * 0.3, thud(0.45, 85, 0.07), np.zeros(int(SR * 0.02))])
    i0 = int(SR * 0.36)
    close[i0:i0 + len(latch)] += latch * 0.7
    W("door_close_wood", close)
    metal_ring = lambda dur, f: sum(np.sin(2 * np.pi * f * k * t_(dur) + k) / k for k in (1, 2.76, 5.4)) * env(int(SR * dur), 0.001, 0.25)
    W("door_open_metal", np.concatenate([latch, creak(1.0, 120, 220, rough=1.0, seed=5) * 0.8]))
    W("door_close_metal", thud(0.5, 60, 0.1) + 0.5 * metal_ring(0.5, 340))
    rattle = np.zeros(int(SR * 0.5))
    for k in range(4):
        c_ = click(0.05, 1500 + 300 * k, 0.01)
        i0 = int(SR * (0.03 + 0.09 * k))
        rattle[i0:i0 + len(c_)] += c_ * (1 - 0.15 * k)
    W("door_locked", rattle + 0.3 * thud(0.5, 110, 0.04))

    # --- elevator --------------------------------------------------------------------------
    dur = 3.0
    t = t_(dur)
    lm = 0.6 * np.sin(2 * np.pi * 50 * t) + 0.35 * np.sin(2 * np.pi * 100 * t) + 0.2 * np.sin(2 * np.pi * 150 * t)
    lm += 0.25 * periodic_noise(dur, 80, 700, -1.0, seed=21) + 0.06 * periodic_noise(dur, 2000, 5000, 0, seed=22)
    lm *= 1 + 0.1 * np.sin(2 * np.pi * (1 / 3) * t)
    W("lift_motor_loop", lm, 0.6)
    d = 1.6
    t = t_(d)
    slide = bandpass(noise(d, 40, 2500, -0.6), 60, 2500) * np.sin(np.pi * t / d) ** 0.5
    slide += 0.3 * np.sin(2 * np.pi * 95 * t) * np.sin(np.pi * t / d)
    end = thud(0.3, 90, 0.05)
    W("lift_doors", np.concatenate([fade(slide, 0.05, 0.05), end]))
    relay = click(0.05, 1300, 0.012)
    W("lift_arrive", np.concatenate([relay, np.zeros(int(SR * 0.12)), thud(0.5, 55, 0.12) + 0.3 * metal_ring(0.5, 210)]))
    W("lift_start", np.concatenate([relay, np.zeros(int(SR * 0.08)), thud(0.4, 48, 0.1)]))
    W("button", click(0.05, 2600, 0.006) + 0.5 * click(0.05, 900, 0.015))

    # --- lights ----------------------------------------------------------------------------
    W("switch", np.concatenate([click(0.04, 3500, 0.003), np.zeros(int(SR * 0.01)), click(0.05, 1800, 0.012) * 0.8]))
    dur = 1.0
    t = t_(dur)
    buzz = sum(np.sin(2 * np.pi * 100 * k * t + k * 0.7) / k ** 1.2 for k in range(1, 14))
    buzz += 0.08 * periodic_noise(dur, 3000, 9000, 0, seed=31)
    W("fluo_buzz_loop", buzz, 0.5)
    sp = np.zeros(int(SR * 0.25))
    for k in range(6):
        c_ = click(0.02, rng.uniform(2000, 6000), 0.002)
        i0 = int(rng.uniform(0, 0.2) * SR)
        sp[i0:i0 + len(c_)] += c_ * rng.uniform(0.4, 1.0)
    W("flicker", sp, 0.6)

    # --- critters --------------------------------------------------------------------------
    for i, (f0, f1, dur) in enumerate(((4200, 6200, 0.12), (3600, 5200, 0.18), (5000, 7000, 0.09))):
        t = t_(dur)
        f = f0 + (f1 - f0) * np.sin(np.pi * t / dur) + 300 * np.sin(2 * np.pi * 45 * t)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / dur) ** 0.6
        sq = np.concatenate([x, np.zeros(int(SR * 0.06)), x[: len(x) * 2 // 3] * 0.6]) if i != 2 else x
        W(f"rat_squeak_{i + 1}", sq, 0.5)
    sc = np.zeros(int(SR * 1.2))
    for k in range(int(1.2 * 22)):
        c_ = bandpass(np.random.default_rng(k).standard_normal(int(SR * 0.012)), 1500, 7000) * np.hanning(int(SR * 0.012))
        i0 = int((k / 22 + rng.uniform(0, 0.02)) * SR)
        if i0 + len(c_) < len(sc):
            sc[i0:i0 + len(c_)] += c_ * rng.uniform(0.3, 1.0)
    W("rat_scurry", fade(sc, 0.05, 0.2), 0.45)
    sk = np.zeros(int(SR * 0.8))
    for k in range(60):
        c_ = click(0.006, rng.uniform(5000, 9000), 0.0008)
        i0 = int(rng.uniform(0, 0.78) * SR)
        sk[i0:i0 + len(c_)] += c_ * rng.uniform(0.2, 0.7)
    W("roach_skitter", fade(sk, 0.05, 0.2), 0.3)

    # --- ambience --------------------------------------------------------------------------
    dur = 24.0
    t = t_(dur)
    drone = 0.6 * periodic_noise(dur, 25, 220, -1.5, seed=41)
    drone += 0.18 * np.sin(2 * np.pi * 55 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * t / dur * 2))
    drone += 0.08 * np.sin(2 * np.pi * 82.5 * t + 1.0) * (0.5 + 0.5 * np.sin(2 * np.pi * t / dur * 3 + 1))
    drone += 0.12 * periodic_noise(dur, 300, 1400, -1.0, seed=42) * (0.5 + 0.5 * np.sin(2 * np.pi * t / dur * 5)) ** 2
    W("ambience_loop", drone, 0.5)
    W("creak_far_1", bandpass(creak(1.6, 90, 150, rough=0.8, seed=51), 100, 1800), 0.6)
    W("creak_far_2", bandpass(creak(2.2, 70, 120, rough=1.0, seed=52), 80, 1200), 0.6)
    tt = t_(0.6)
    drip = np.sin(2 * np.pi * np.cumsum(1400 + 1600 * np.exp(-tt / 0.01)) / SR) * env(len(tt), 0.0005, 0.03)
    echo = np.zeros_like(drip)
    i0 = int(SR * 0.25)
    echo[i0:] = drip[: len(drip) - i0] * 0.2
    W("drip", fade(drip + echo, 0, 0.05), 0.4)
    knocks = np.zeros(int(SR * 1.5))
    for k, tk in enumerate((0.0, 0.32, 0.55, 1.1)):
        th = thud(0.3, 140 - 15 * k, 0.03) + 0.4 * metal_ring(0.3, 420)
        i0 = int(tk * SR)
        knocks[i0:i0 + len(th)] += th * (1 - 0.15 * k)
    W("pipes_knock", bandpass(knocks, 60, 3000), 0.5)
    dur = 4.0
    t = t_(dur)
    wind = bandpass(noise(dur, 100, 2000, -0.8), 150, 1600)
    wind *= np.sin(np.pi * t / dur) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t))
    W("wind_gust", fade(wind, 0.2, 0.3), 0.4)
    slam = thud(1.2, 65, 0.2)
    W("door_slam_far", bandpass(slam, 40, 900), 0.6)
    tt = t_(1.4)
    hum = np.sin(2 * np.pi * 410 * tt) * env(len(tt), 0.3, 0.6) * (0.5 + 0.5 * np.sin(2 * np.pi * 4.5 * tt))
    W("whisper_far", fade(bandpass(hum + 0.6 * bandpass(noise(1.4), 900, 4000) * env(len(tt), 0.4, 0.5), 200, 5000),
                          0.2, 0.3), 0.25)
    return sorted(f for f in os.listdir(out) if f.endswith(".wav"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "game",
                                                  "assets", "sfx"))
    a = ap.parse_args()
    files = make_all(a.out)
    print(len(files), "files:", " ".join(files))

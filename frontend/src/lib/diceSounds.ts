/** Procedural tabletop dice SFX via Web Audio — no asset files. */

let sharedCtx: AudioContext | null = null;

function ctx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  const AC =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  if (!AC) return null;
  if (!sharedCtx) sharedCtx = new AC();
  if (sharedCtx.state === "suspended") void sharedCtx.resume();
  return sharedCtx;
}

function noiseBurst(
  audio: AudioContext,
  opts: { duration: number; gain: number; freq?: number; q?: number },
) {
  const duration = opts.duration;
  const gain = opts.gain;
  const freq = opts.freq ?? 800;
  const sampleRate = audio.sampleRate;
  const length = Math.max(1, Math.floor(sampleRate * duration));
  const buffer = audio.createBuffer(1, length, sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) {
    const t = i / length;
    data[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, 1.6);
  }
  const src = audio.createBufferSource();
  src.buffer = buffer;
  const filter = audio.createBiquadFilter();
  filter.type = "bandpass";
  filter.frequency.value = freq;
  filter.Q.value = opts.q ?? 0.9;
  const g = audio.createGain();
  g.gain.value = gain;
  src.connect(filter);
  filter.connect(g);
  g.connect(audio.destination);
  src.start();
}

function woodThud(audio: AudioContext, intensity: number) {
  const osc = audio.createOscillator();
  const g = audio.createGain();
  osc.type = "sine";
  const t0 = audio.currentTime;
  const i = Math.max(0.15, Math.min(1, intensity));
  osc.frequency.setValueAtTime(90 + 40 * i, t0);
  osc.frequency.exponentialRampToValueAtTime(38, t0 + 0.12 + 0.08 * i);
  g.gain.setValueAtTime(0.08 + 0.28 * i, t0);
  g.gain.exponentialRampToValueAtTime(0.001, t0 + 0.16 + 0.1 * i);
  osc.connect(g);
  g.connect(audio.destination);
  osc.start();
  osc.stop(t0 + 0.3);
}

/** Hard plastic/resin click against wood — call on each table bounce. */
export function playTableBounce(intensity = 0.6) {
  const audio = ctx();
  if (!audio) return;
  const i = Math.max(0.12, Math.min(1, intensity));
  noiseBurst(audio, {
    duration: 0.035 + 0.025 * i,
    gain: 0.1 + 0.22 * i,
    freq: 500 + 700 * i,
    q: 1.2,
  });
  woodThud(audio, i);
  if (i > 0.45) {
    window.setTimeout(() => {
      noiseBurst(audio, { duration: 0.02, gain: 0.06 * i, freq: 1400, q: 0.7 });
    }, 18);
  }
}

/** Soft scrape while sliding to a stop. */
export function playTableSlide() {
  const audio = ctx();
  if (!audio) return;
  noiseBurst(audio, { duration: 0.12, gain: 0.07, freq: 280, q: 0.5 });
}

export function playDiceLand() {
  playTableBounce(0.85);
  window.setTimeout(() => playTableSlide(), 50);
}

export function playDiceCrit(success: boolean) {
  const audio = ctx();
  if (!audio) return;
  const osc = audio.createOscillator();
  const g = audio.createGain();
  osc.type = "triangle";
  const t0 = audio.currentTime;
  if (success) {
    osc.frequency.setValueAtTime(523, t0);
    osc.frequency.setValueAtTime(784, t0 + 0.09);
    osc.frequency.setValueAtTime(1046, t0 + 0.18);
  } else {
    osc.frequency.setValueAtTime(196, t0);
    osc.frequency.exponentialRampToValueAtTime(70, t0 + 0.4);
  }
  g.gain.setValueAtTime(0.14, t0);
  g.gain.exponentialRampToValueAtTime(0.001, t0 + 0.45);
  osc.connect(g);
  g.connect(audio.destination);
  osc.start();
  osc.stop(t0 + 0.48);
}

/** Unlock audio on the click that starts the toss. */
export function unlockDiceAudio() {
  ctx();
}

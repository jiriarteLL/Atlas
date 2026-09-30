// sonido.js — Ambiente sonoro generado con WebAudio (sin archivos de audio).
// Un acorde suave con filtro pasabajos que respira; arranca y se apaga con fundido.
let audio = null;

export function iniciarSonido() {
  if (audio) return;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  const ctx = new AC();
  const master = ctx.createGain();
  master.gain.setValueAtTime(0.0001, ctx.currentTime);
  master.gain.exponentialRampToValueAtTime(0.16, ctx.currentTime + 2.5);

  const filtro = ctx.createBiquadFilter();
  filtro.type = "lowpass";
  filtro.frequency.value = 850;
  filtro.Q.value = 3.5;
  master.connect(filtro);
  filtro.connect(ctx.destination);

  const lfo = ctx.createOscillator();
  const lfoGain = ctx.createGain();
  lfo.frequency.value = 0.05;
  lfoGain.gain.value = 480;
  lfo.connect(lfoGain);
  lfoGain.connect(filtro.frequency);
  lfo.start();

  const nodos = [lfo];
  [110, 164.81, 220, 277.18, 329.63].forEach((f, i) => {
    const o = ctx.createOscillator();
    o.type = i % 2 ? "triangle" : "sine";
    o.frequency.value = f;
    o.detune.value = (i - 2) * 5;
    const g = ctx.createGain();
    g.gain.value = i === 0 ? 0.34 : 0.16;
    const trem = ctx.createOscillator();
    const tg = ctx.createGain();
    trem.frequency.value = 0.08 + i * 0.035;
    tg.gain.value = g.gain.value * 0.45;
    trem.connect(tg);
    tg.connect(g.gain);
    trem.start();
    o.connect(g);
    g.connect(master);
    o.start();
    nodos.push(o, trem);
  });
  audio = { ctx, master, nodos };
}

export function detenerSonido() {
  const a = audio;
  if (!a) return;
  audio = null;
  try {
    a.master.gain.cancelScheduledValues(a.ctx.currentTime);
    a.master.gain.setValueAtTime(a.master.gain.value, a.ctx.currentTime);
    a.master.gain.exponentialRampToValueAtTime(0.0001, a.ctx.currentTime + 1.2);
    setTimeout(() => { a.nodos.forEach((n) => { try { n.stop(); } catch { /* ya parado */ } }); a.ctx.close(); }, 1400);
  } catch { try { a.ctx.close(); } catch { /* nada */ } }
}

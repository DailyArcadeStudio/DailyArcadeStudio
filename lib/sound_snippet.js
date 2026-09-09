// ---------- sound: everything synthesised, no audio files ----------
// Keeps the single-HTML rule (nothing to download) and lets the music
// react to play: the bass line speeds up with the game, events drop a
// stinger, and the whole thing ducks out on a game over.
const SND = (() => {
  let ctx = null, master = null, musicGain = null, on = true, started = false;
  let step = 0, timer = null, tempo = 0.25;

  // A pentatonic scale never sounds wrong against itself, which matters
  // when the tempo drifts with the player's speed.
  const SCALE = [0, 3, 5, 7, 10];
  const ROOT = 220;
  const hz = (deg, oct = 0) =>
    ROOT * Math.pow(2, oct + Math.floor(deg / SCALE.length)) *
    Math.pow(2, SCALE[((deg % SCALE.length) + SCALE.length) % SCALE.length] / 12);

  function ensure() {
    if (ctx) return ctx;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.32;
    master.connect(ctx.destination);
    musicGain = ctx.createGain();
    musicGain.gain.value = 1;
    musicGain.connect(master);
    return ctx;
  }

  function blip(freq, dur, type = 'square', vol = 0.25, dest = null, slideTo = null) {
    if (!ctx || !on) return;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, ctx.currentTime);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, ctx.currentTime + dur);
    // a short attack stops every note from clicking
    g.gain.setValueAtTime(0, ctx.currentTime);
    g.gain.linearRampToValueAtTime(vol, ctx.currentTime + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    o.connect(g); g.connect(dest || master);
    o.start(); o.stop(ctx.currentTime + dur + 0.02);
  }

  function noise(dur, vol = 0.2, hp = 800) {
    if (!ctx || !on) return;
    const n = Math.floor(ctx.sampleRate * dur);
    const buf = ctx.createBuffer(1, n, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const src = ctx.createBufferSource(); src.buffer = buf;
    const f = ctx.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = hp;
    const g = ctx.createGain(); g.gain.value = vol;
    src.connect(f); f.connect(g); g.connect(master);
    src.start();
  }

  // --- the loop: a walking bass plus an offbeat blip ---
  function tick() {
    if (!ctx || !on) return;
    const bar = step % 16;
    if (bar % 4 === 0) blip(hz(bar === 0 ? 0 : 2, -1), tempo * 1.6, 'triangle', 0.30, musicGain);
    if (bar % 8 === 4) blip(hz(4, 0), tempo * 0.7, 'square', 0.10, musicGain);
    if (bar % 4 === 2) noise(0.05, 0.05, 4000);           // hat
    step++;
    timer = setTimeout(tick, tempo * 1000);
  }

  return {
    // must be called from a user gesture — browsers block audio otherwise
    start() {
      if (!ensure() || started) return;
      if (ctx.state === 'suspended') ctx.resume();
      started = true; step = 0; tick();
    },
    stop() { if (timer) { clearTimeout(timer); timer = null; } started = false; },
    /** speed the music up with the game; 1 = starting pace */
    setPace(mult) { tempo = Math.max(0.11, 0.25 / Math.max(0.2, mult)); },
    duck(sec = 1.6) {                                      // for game over
      if (!ctx) return;
      musicGain.gain.cancelScheduledValues(ctx.currentTime);
      musicGain.gain.setValueAtTime(musicGain.gain.value, ctx.currentTime);
      musicGain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + sec);
    },
    unduck() {
      if (!ctx) return;
      musicGain.gain.cancelScheduledValues(ctx.currentTime);
      musicGain.gain.setValueAtTime(0.0001, ctx.currentTime);
      musicGain.gain.exponentialRampToValueAtTime(1, ctx.currentTime + 0.4);
    },
    // --- one-shots ---
    move()  { ensure(); blip(660, 0.07, 'square', 0.12); },
    jump()  { ensure(); blip(420, 0.16, 'square', 0.18, null, 900); },
    land()  { ensure(); noise(0.06, 0.10, 500); },
    place() { ensure(); blip(520, 0.10, 'triangle', 0.22, null, 700); },
    event() { ensure(); [0, 90, 180].forEach((ms, i) =>
                setTimeout(() => blip(hz(2 + i, 0), 0.18, 'sawtooth', 0.20), ms)); },
    hit()   { ensure(); noise(0.35, 0.30, 200);
              blip(180, 0.5, 'sawtooth', 0.28, null, 40); },
    over()  { ensure(); [0, 140, 280, 460].forEach((ms, i) =>
                setTimeout(() => blip(hz(-i, -1), 0.42, 'triangle', 0.26), ms)); },
    toggle() { on = !on; if (!on) { this.stop(); } else { this.start(); } return on; },
    get enabled() { return on; },
  };
})();

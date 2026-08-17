import { useEffect, useRef } from "react";

/**
 * Ambient background for screens 1-8.
 *
 * One motif per screen, chosen to match what that screen is actually about
 * rather than decorating all eight the same way:
 *
 *   1 User Input .......... data particles flowing through circuit traces
 *   2 Display Results ..... pulses travelling between server racks
 *   3 Visualization ....... a data stream running chips -> AI -> human
 *   4 Interactivity ....... holographic UI rings around the operator
 *   5 Particle Management . a semiconductor wafer rotating extremely slowly
 *   6 Cleanliness ......... cloud infrastructure drifting, air moving through
 *   7 AI Precision ........ neural nodes gently illuminating in sequence
 *   8 Data Learning ....... India appearing through connected nodes
 *
 * Screen 9 has no field. Its beamline is already a simulation and a second
 * moving layer behind it would fight for the same attention.
 *
 * ---------------------------------------------------------------------------
 * Restraint is the whole design
 *
 * Everything here runs at a few percent alpha in the screen's own accent
 * colour, and every motion is slow — a wafer turning once every two minutes, a
 * particle crossing the screen in twenty seconds. These sit behind live
 * numbers a judge is reading. Anything faster or heavier stops being
 * atmosphere and becomes a distraction, and the panels above are frosted
 * glass, so whatever moves here is already blurred and dimmed before it
 * reaches the eye.
 *
 * Deterministic: a small seeded generator, no Math.random, so a screen looks
 * the same every time it is opened and there is no frame where the layout
 * suddenly rearranges.
 *
 * Canvas, no library. Same constraint as everything else here — a third-party
 * runtime dependency would break the offline claim demo_proof.py certifies.
 */

/* Deterministic PRNG. Same seed, same field, every visit. */
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/* India, simplified to ~30 vertices in lon/lat. Enough to be recognisable at
   a glance and honest about being a sketch — this is an outline traced by
   nodes, not a survey boundary, and nothing is measured from it. */
const INDIA = [
  [77.0, 35.4], [74.4, 32.5], [71.9, 30.1], [69.6, 27.5], [68.2, 23.9],
  [70.0, 22.6], [72.7, 21.4], [72.9, 19.1], [73.5, 16.4], [74.8, 13.0],
  [76.3, 10.2], [77.5, 8.1], [79.2, 10.3], [80.3, 13.1], [81.2, 15.7],
  [82.9, 17.0], [85.0, 19.5], [86.9, 20.7], [88.1, 21.7], [88.9, 24.2],
  [89.7, 25.9], [92.0, 26.6], [94.2, 27.4], [95.8, 27.9], [93.3, 28.6],
  [90.4, 28.1], [88.1, 27.5], [85.0, 28.4], [81.0, 30.3], [78.5, 32.4],
];

function normIndia(w, h) {
  const lo0 = 67.5, lo1 = 96.5, la0 = 7.0, la1 = 36.5;
  const box = Math.min(w * 0.42, h * 0.82);
  const cx = w * 0.5, cy = h * 0.5;
  return INDIA.map(([lo, la]) => [
    cx + ((lo - lo0) / (lo1 - lo0) - 0.5) * box * 0.92,
    // Latitude runs the other way on screen, and India is taller than wide.
    cy - ((la - la0) / (la1 - la0) - 0.5) * box,
  ]);
}

/* The nine screen accents were picked to label data on white panels, so they
   are mid-tone by design — #e0a33c amber against #e4f1e6 mint is barely a
   luminance step, and at a tenth of an alpha it is nothing at all. Each is
   pulled most of the way toward the page ink first, which keeps the hue (so a
   screen still reads as "its" colour) while giving the stroke something to
   contrast against. */
const INK = [16, 30, 23];
const DARKEN = 0.52;

const hex2rgb = (h) => {
  const raw = [
    parseInt(h.slice(1, 3), 16),
    parseInt(h.slice(3, 5), 16),
    parseInt(h.slice(5, 7), 16),
  ];
  return raw.map((c, i) => Math.round(c + (INK[i] - c) * DARKEN));
};

const DRAW = {
  /* 1 — data particles flowing through circuit traces --------------------- */
  1(ctx, t, w, h, A) {
    const r = rng(0x1111);
    const lanes = 9;
    for (let i = 0; i < lanes; i++) {
      const y0 = h * (0.1 + 0.8 * (i / (lanes - 1)));
      const kink = w * (0.25 + r() * 0.5);
      const y1 = y0 + (r() - 0.5) * h * 0.22;
      // Right-angle routing, the way a trace is actually laid out.
      ctx.strokeStyle = `rgba(${A}, 0.215)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, y0);
      ctx.lineTo(kink, y0);
      ctx.lineTo(kink, y1);
      ctx.lineTo(w, y1);
      ctx.stroke();
      // Pads at the corner.
      ctx.fillStyle = `rgba(${A}, 0.344)`;
      ctx.beginPath();
      ctx.arc(kink, y0, 2.2, 0, Math.PI * 2);
      ctx.fill();

      // Two particles per lane, ~20s to cross.
      for (let k = 0; k < 2; k++) {
        const p = ((t * 0.05 + i * 0.13 + k * 0.5) % 1);
        const total = kink + Math.abs(y1 - y0) + (w - kink);
        const d = p * total;
        let x, y;
        if (d < kink) { x = d; y = y0; }
        else if (d < kink + Math.abs(y1 - y0)) {
          x = kink; y = y0 + Math.sign(y1 - y0) * (d - kink);
        } else { x = kink + (d - kink - Math.abs(y1 - y0)); y = y1; }
        const g = ctx.createRadialGradient(x, y, 0, x, y, 7);
        g.addColorStop(0, `rgba(${A}, 0.62)`);
        g.addColorStop(1, `rgba(${A}, 0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, 7, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  },

  /* 2 — pulses travelling between server racks ---------------------------- */
  2(ctx, t, w, h, A) {
    const n = 5;
    const gap = w / (n + 1);
    const rackW = Math.min(46, gap * 0.34);
    const rackH = Math.min(h * 0.3, 150);
    const ys = h * 0.5;
    const xs = [];
    for (let i = 0; i < n; i++) xs.push(gap * (i + 1));

    // Racks.
    for (let i = 0; i < n; i++) {
      const x = xs[i];
      ctx.strokeStyle = `rgba(${A}, 0.279)`;
      ctx.lineWidth = 1;
      ctx.strokeRect(x - rackW / 2, ys - rackH / 2, rackW, rackH);
      // Blade slots, one lighting up per rack on its own cycle.
      const slots = 7;
      for (let k = 0; k < slots; k++) {
        const y = ys - rackH / 2 + ((k + 0.5) / slots) * rackH;
        const lit = (Math.sin(t * 0.9 + i * 1.7 + k * 0.6) + 1) / 2;
        ctx.fillStyle = `rgba(${A}, ${0.05 + lit * 0.12})`;
        ctx.fillRect(x - rackW / 2 + 4, y - 2, rackW - 8, 3);
      }
    }

    // Links and pulses.
    for (let i = 0; i < n - 1; i++) {
      ctx.strokeStyle = `rgba(${A}, 0.215)`;
      ctx.beginPath();
      ctx.moveTo(xs[i] + rackW / 2, ys);
      ctx.lineTo(xs[i + 1] - rackW / 2, ys);
      ctx.stroke();
      const p = (t * 0.32 + i * 0.24) % 1;
      const x = xs[i] + rackW / 2 + (xs[i + 1] - xs[i] - rackW) * p;
      const g = ctx.createRadialGradient(x, ys, 0, x, ys, 9);
      g.addColorStop(0, `rgba(${A}, 0.62)`);
      g.addColorStop(1, `rgba(${A}, 0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, ys, 9, 0, Math.PI * 2);
      ctx.fill();
    }
  },

  /* 3 — data stream: chips -> AI -> human --------------------------------- */
  3(ctx, t, w, h, A) {
    const y = h * 0.5;
    const x0 = w * 0.16, x1 = w * 0.5, x2 = w * 0.84;

    // Chips (left): three small squares with pin ticks.
    for (let i = 0; i < 3; i++) {
      const cy2 = y + (i - 1) * h * 0.16;
      const s = 18;
      ctx.strokeStyle = `rgba(${A}, 0.301)`;
      ctx.lineWidth = 1;
      ctx.strokeRect(x0 - s / 2, cy2 - s / 2, s, s);
      for (let k = 0; k < 4; k++) {
        const py = cy2 - s / 2 + ((k + 0.5) / 4) * s;
        ctx.beginPath();
        ctx.moveTo(x0 + s / 2, py);
        ctx.lineTo(x0 + s / 2 + 5, py);
        ctx.stroke();
      }
    }
    // AI (middle): a small node cluster.
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2 + t * 0.05;
      const rr = 24;
      ctx.fillStyle = `rgba(${A}, 0.387)`;
      ctx.beginPath();
      ctx.arc(x1 + Math.cos(a) * rr, y + Math.sin(a) * rr * 0.8, 2.4, 0, Math.PI * 2);
      ctx.fill();
    }
    // Human (right): head and shoulders, one continuous stroke each.
    ctx.strokeStyle = `rgba(${A}, 0.344)`;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.arc(x2, y - 16, 11, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x2, y + 34, 26, Math.PI * 1.15, Math.PI * 1.85);
    ctx.stroke();

    // The stream itself.
    ctx.strokeStyle = `rgba(${A}, 0.193)`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x0 + 14, y);
    ctx.lineTo(x2 - 20, y);
    ctx.stroke();
    for (let i = 0; i < 7; i++) {
      const p = (t * 0.055 + i / 7) % 1;
      const x = x0 + 14 + (x2 - 20 - x0 - 14) * p;
      // Brightest as it passes through the model.
      const near = Math.exp(-Math.pow((x - x1) / (w * 0.14), 2));
      const g = ctx.createRadialGradient(x, y, 0, x, y, 8);
      g.addColorStop(0, `rgba(${A}, ${0.28 + near * 0.35})`);
      g.addColorStop(1, `rgba(${A}, 0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fill();
    }
  },

  /* 4 — holographic UI rings --------------------------------------------- */
  4(ctx, t, w, h, A) {
    const cx = w * 0.5, cy = h * 0.5;
    const base = Math.min(w * 0.3, h * 0.42);
    const RINGS = [
      { r: 1.0, from: 0.1, span: 1.1, spd: 0.07 },
      { r: 0.82, from: 2.4, span: 1.6, spd: -0.05 },
      { r: 0.64, from: 4.2, span: 0.9, spd: 0.1 },
      { r: 0.46, from: 1.2, span: 2.2, spd: -0.08 },
    ];
    for (const ring of RINGS) {
      const rr = base * ring.r;
      const a0 = ring.from + t * ring.spd;
      ctx.strokeStyle = `rgba(${A}, 0.279)`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(cx, cy, rr, a0, a0 + ring.span);
      ctx.stroke();
      // Tick at each end of the arc.
      for (const a of [a0, a0 + ring.span]) {
        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(a) * (rr - 4), cy + Math.sin(a) * (rr - 4));
        ctx.lineTo(cx + Math.cos(a) * (rr + 4), cy + Math.sin(a) * (rr + 4));
        ctx.stroke();
      }
    }
    // Graduated outer scale.
    ctx.strokeStyle = `rgba(${A}, 0.193)`;
    for (let i = 0; i < 48; i++) {
      const a = (i / 48) * Math.PI * 2;
      const rr = base * 1.14;
      const len = i % 6 === 0 ? 7 : 3;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
      ctx.lineTo(cx + Math.cos(a) * (rr + len), cy + Math.sin(a) * (rr + len));
      ctx.stroke();
    }
  },

  /* 5 — semiconductor wafer, rotating extremely slowly -------------------- */
  5(ctx, t, w, h, A) {
    const cx = w * 0.5, cy = h * 0.5;
    const R = Math.min(w * 0.28, h * 0.42);
    // One revolution every ~2 minutes.
    const rot = t * 0.052;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rot);

    ctx.strokeStyle = `rgba(${A}, 0.344)`;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.arc(0, 0, R, 0, Math.PI * 2);
    ctx.stroke();

    // Orientation notch.
    ctx.beginPath();
    ctx.moveTo(0, -R);
    ctx.lineTo(-R * 0.06, -R * 0.93);
    ctx.lineTo(R * 0.06, -R * 0.93);
    ctx.closePath();
    ctx.stroke();

    // Die grid, clipped to the wafer.
    ctx.save();
    ctx.beginPath();
    ctx.arc(0, 0, R * 0.985, 0, Math.PI * 2);
    ctx.clip();
    const step = R / 5.5;
    ctx.strokeStyle = `rgba(${A}, 0.215)`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = -R; x <= R; x += step) {
      ctx.moveTo(x, -R); ctx.lineTo(x, R);
      ctx.moveTo(-R, x); ctx.lineTo(R, x);
    }
    ctx.stroke();
    // A stepper walking the shot map: one die lit at a time.
    const cols = Math.floor((R * 2) / step);
    const idx = Math.floor(t * 0.5) % Math.max(1, cols * cols);
    const dx = -R + (idx % cols) * step;
    const dy = -R + Math.floor(idx / cols) * step;
    if (Math.hypot(dx + step / 2, dy + step / 2) < R * 0.9) {
      ctx.fillStyle = `rgba(${A}, 0.301)`;
      ctx.fillRect(dx, dy, step, step);
    }
    ctx.restore();
    ctx.restore();
  },

  /* 6 — cloud infrastructure, air moving through -------------------------- */
  6(ctx, t, w, h, A) {
    const r = rng(0x6060);
    for (let i = 0; i < 5; i++) {
      const baseX = w * (0.12 + r() * 0.76);
      const y = h * (0.16 + r() * 0.68);
      const s = Math.min(w, h) * (0.07 + r() * 0.06);
      // Drift, each cloud on its own slow cycle.
      const x = baseX + Math.sin(t * 0.06 + i * 1.9) * w * 0.02;
      ctx.strokeStyle = `rgba(${A}, 0.258)`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(x - s * 0.5, y, s * 0.5, Math.PI * 0.6, Math.PI * 1.7);
      ctx.arc(x, y - s * 0.34, s * 0.56, Math.PI * 1.1, Math.PI * 1.95);
      ctx.arc(x + s * 0.6, y, s * 0.46, Math.PI * 1.4, Math.PI * 0.45);
      ctx.closePath();
      ctx.stroke();
    }
    // Filtered airflow: slow laminar streaks, top to bottom.
    for (let i = 0; i < 16; i++) {
      const x = w * ((i + 0.5) / 16);
      const p = ((t * 0.07 + i * 0.061) % 1);
      const y = -h * 0.1 + p * h * 1.2;
      const g = ctx.createLinearGradient(0, y - 34, 0, y + 34);
      g.addColorStop(0, `rgba(${A}, 0)`);
      g.addColorStop(0.5, `rgba(${A}, 0.301)`);
      g.addColorStop(1, `rgba(${A}, 0)`);
      ctx.strokeStyle = g;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, y - 34);
      ctx.lineTo(x, y + 34);
      ctx.stroke();
    }
  },

  /* 7 — neural nodes gently illuminating ---------------------------------- */
  7(ctx, t, w, h, A) {
    const LAYERS = [4, 6, 6, 3];
    const nodes = [];
    LAYERS.forEach((n, li) => {
      const x = w * (0.2 + (li / (LAYERS.length - 1)) * 0.6);
      for (let i = 0; i < n; i++) {
        nodes.push({
          x,
          y: h * (0.5 + ((i - (n - 1) / 2) / Math.max(1, n)) * 0.62),
          li,
          i,
        });
      }
    });
    // Edges first, so nodes sit on top.
    ctx.lineWidth = 1;
    for (const a of nodes) {
      for (const b of nodes) {
        if (b.li !== a.li + 1) continue;
        ctx.strokeStyle = `rgba(${A}, 0.118)`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
    // Illumination sweeps left to right, layer by layer.
    for (const n of nodes) {
      const phase = (t * 0.34 - n.li * 0.55 + n.i * 0.12) % 3;
      const lit = phase > 0 && phase < 1 ? Math.sin(phase * Math.PI) : 0;
      const rr = 3.4 + lit * 2.6;
      const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, rr * 3);
      g.addColorStop(0, `rgba(${A}, ${0.16 + lit * 0.45})`);
      g.addColorStop(1, `rgba(${A}, 0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(n.x, n.y, rr * 3, 0, Math.PI * 2);
      ctx.fill();
    }
  },

  /* 8 — India appearing through connected nodes --------------------------- */
  8(ctx, t, w, h, A) {
    const pts = normIndia(w, h);
    const n = pts.length;
    // The outline draws itself in over ~24s, holds, then restarts.
    const cycle = (t % 30) / 24;
    const shown = Math.min(1, cycle) * n;

    ctx.lineWidth = 1.3;
    ctx.strokeStyle = `rgba(${A}, 0.43)`;
    ctx.beginPath();
    for (let i = 0; i < Math.floor(shown); i++) {
      const p = pts[i];
      if (i === 0) ctx.moveTo(p[0], p[1]);
      else ctx.lineTo(p[0], p[1]);
    }
    // Close the loop once every vertex is in.
    if (shown >= n) ctx.closePath();
    ctx.stroke();

    // Nodes, brightest at the drawing head.
    for (let i = 0; i < n; i++) {
      const on = i < shown;
      if (!on) continue;
      const head = Math.max(0, 1 - (shown - i) / 3);
      const p = pts[i];
      const rr = 2.4 + head * 3;
      const g = ctx.createRadialGradient(p[0], p[1], 0, p[0], p[1], rr * 3);
      g.addColorStop(0, `rgba(${A}, ${0.22 + head * 0.5})`);
      g.addColorStop(1, `rgba(${A}, 0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(p[0], p[1], rr * 3, 0, Math.PI * 2);
      ctx.fill();
    }
  },
};

export function ScreenField({ variant, accent = "#4f9490" }) {
  const ref = useRef(null);
  const varRef = useRef(variant);
  const accRef = useRef(accent);
  varRef.current = variant;
  accRef.current = accent;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")
      ?.matches;

    const ctx = canvas.getContext("2d");
    let raf = 0;
    let w = 0;
    let h = 0;
    let dpr = 1;
    let paint = () => {};

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = Math.max(1, Math.floor(rect.width));
      h = Math.max(1, Math.floor(rect.height));
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      paint(performance.now());
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    window.addEventListener("resize", resize);

    // Not from zero, and not merely a little way in: several motifs begin
    // empty at t=0, and the India outline in particular takes 24s to trace
    // itself. At a 5s offset it opened as a stray squiggle. The first frame is
    // the ONLY frame in a backgrounded or non-compositing tab, so the clock
    // starts far enough along that every motif opens fully formed — India at
    // 25 of its 30 vertices, the wafer already a radian into its turn.
    const start = performance.now() - 20000;

    const render = (now) => {
      const t = (now - start) / 1000;
      const draw = DRAW[varRef.current];
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      if (!draw) return;
      const [r, g, b] = hex2rgb(accRef.current);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      draw(ctx, t, w, h, `${r}, ${g}, ${b}`);
    };

    paint = render;
    render(performance.now());

    if (!reduce) {
      const loop = (now) => {
        render(now);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, []);

  // Keyed on variant so switching screens remounts and restarts the motif from
  // its opening frame rather than dropping in halfway through the last one.
  return <canvas className="screen-field" ref={ref} aria-hidden="true" />;
}

import { useEffect, useRef } from "react";
import {
  orbRuns,
  WORDMARK,
  WORDMARK_INK,
  wordmarkTransform,
} from "../lib/orb.js";

/**
 * Masthead mark — the orb.
 *
 * A sphere woven out of flowing light-trails: great circles with precessing
 * axes, hollow through the middle, magenta on one flank and electric blue on
 * the other. The geometry, the palette and the letterforms all live in
 * ../lib/orb.js, which also generates public/logo.svg, logo-mono.svg and
 * favicon.svg, so the mark cannot drift between the app and the files handed
 * to anyone outside it.
 *
 * Canvas rather than SVG. The drawing is ~1,500 short strokes whose colour,
 * opacity and width change every frame; as DOM that is a few thousand nodes
 * being restyled sixty times a second. No library — three.js or an SVG filter
 * package would put third-party runtime code inside the bundle demo_proof.py
 * certifies runs with the network pulled.
 *
 * ---------------------------------------------------------------------------
 * Neon on a white page
 *
 * The reference glows because it is additive light on black. On white there is
 * no headroom to add to, so `lighter` renders nothing, and painting a dark
 * disc under the orb to add onto leaves a grey halo where the disc feathers
 * out. This draws the subtractive translation instead: saturated colour at low
 * alpha composited with `multiply`, so crossings deepen and saturate rather
 * than blowing out. That is what silk-over-a-lightbox looks like in print, and
 * it carries the same information — density where the ribbons pile up.
 *
 * The canvas keeps its alpha channel and no ground is painted. With a
 * transparent backdrop the first stroke of `multiply` behaves exactly like
 * source-over and only subsequent overlaps darken, so the mark composites onto
 * whatever it is sitting on with no box and no halo.
 *
 * ---------------------------------------------------------------------------
 * Two cuts
 *
 * The brief puts "euv" in the hollow. At the masthead's 42px the hollow is
 * about 17px across and the word would be ~12px wide — under 4px per letter,
 * with a stroke a fifth of a pixel. That is not small type, it is a smudge, so
 * the small cut does not carry it. The word is drawn only at >= 96px, which is
 * the size logo.svg and the print/slide lockup use. `text` can force either
 * way if a caller knows better.
 *
 * ---------------------------------------------------------------------------
 * First paint
 *
 * requestAnimationFrame does not tick in a backgrounded or non-compositing
 * tab, and neither do ResizeObserver callbacks. So a frame is painted
 * synchronously on mount and again at the end of every resize; the animation
 * loop is an enhancement on top of a mark that is already correct.
 */

/* Detail tiers, keyed on the rendered size in CSS pixels. A logo is not one
   drawing at several sizes: below ~64px the haze passes stop being a field and
   start being fog over the core, and fifteen strands in a 42px circle is mush,
   which is exactly how the previous multi-loop mark failed. */
function tier(size) {
  if (size >= 220) {
    return {
      count: 17,
      samples: 156,
      passes: ["glow", "haze", "mid", "core", "spec"],
      gain: 1,
      envAmt: 0.5,
      holeIn: 0.46,
      holeOut: 0.8,
    };
  }
  if (size >= 96) {
    return {
      count: 14,
      samples: 140,
      passes: ["glow", "haze", "mid", "core", "spec"],
      gain: 1.05,
      envAmt: 0.46,
      holeIn: 0.44,
      holeOut: 0.78,
    };
  }
  if (size >= 56) {
    return {
      count: 10,
      samples: 120,
      passes: ["haze", "mid", "core"],
      gain: 1.2,
      envAmt: 0.34,
      holeIn: 0.4,
      holeOut: 0.72,
    };
  }
  // Masthead and smaller. Fewer strands, a tighter hollow and no glow: at this
  // size the wide passes are fog over the core rather than a field around it,
  // and a ribbon that fades out mid-loop is just a bite taken out of the ring.
  return {
    count: 8,
    samples: 108,
    passes: ["haze", "mid", "core"],
    gain: 1.6,
    envAmt: 0.15,
    holeIn: 0.38,
    holeOut: 0.7,
  };
}

function readInk(el) {
  const c = getComputedStyle(el).color || "rgb(15,17,21)";
  const m = c.match(/-?[\d.]+/g);
  if (!m || m.length < 3) return [15, 17, 21];
  return [Number(m[0]), Number(m[1]), Number(m[2])];
}

export function Mark({
  mono = false,
  className = "mark",
  text = "auto",
  /* Set on a dark ground. orb.js composites with `multiply` because it was
     drawn for a white page; over darkness that darkens crossings, which is
     backwards. Additive turns the ribbons back into light. */
  additive = false,
}) {
  const ref = useRef(null);
  const monoRef = useRef(mono);
  const textRef = useRef(text);
  const addRef = useRef(additive);
  monoRef.current = mono;
  textRef.current = text;
  addRef.current = additive;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")
      ?.matches;

    const ctx = canvas.getContext("2d");
    let raf = 0;
    let size = 0;
    let dpr = 1;
    let glyphs = null;
    let paint = () => {};

    const render = (now) => {
      if (!size) return;
      const t = (now - start) / 1000;
      const cfg = tier(size);
      const inkRgb = monoRef.current ? readInk(canvas) : null;

      ctx.clearRect(0, 0, size, size);
      ctx.lineJoin = "round";

      const runs = orbRuns({
        size,
        // Slow. The reference twists rather than spins; anything faster reads
        // as a loading spinner, which is the one thing a logo must not be.
        time: t * 0.42,
        count: cfg.count,
        samples: cfg.samples,
        passes: cfg.passes,
        gain: cfg.gain,
        envAmt: cfg.envAmt,
        holeIn: cfg.holeIn,
        holeOut: cfg.holeOut,
        // Below ~1 device pixel a stroke is spread by antialiasing and goes
        // pale whatever colour it is, so the width is floored at one.
        minWidth: Math.max(0.5, 1 / dpr),
        mono: inkRgb,
        precision: 3,
        // Over a dark ground the far side of the sphere has to recede INTO
        // the ground rather than wash toward the page.
        dark: addRef.current,
      });

      let op = "";
      let cap = "";
      for (const r of runs) {
        const wanted =
          addRef.current && r.op === "multiply" ? "lighter" : r.op;
        if (wanted !== op) {
          op = wanted;
          ctx.globalCompositeOperation = op;
        }
        if (r.cap !== cap) {
          cap = r.cap;
          ctx.lineCap = cap;
        }
        // Additive accumulates far faster than subtractive; the alphas that
        // read as silk on white saturate to a flat ring on black.
        ctx.globalAlpha = op === "lighter" ? r.alpha * 0.45 : r.alpha;
        ctx.strokeStyle = r.color;
        ctx.lineWidth = r.width;
        ctx.beginPath();
        ctx.moveTo(r.pts[0], r.pts[1]);
        for (let i = 2; i < r.pts.length; i += 2) ctx.lineTo(r.pts[i], r.pts[i + 1]);
        ctx.stroke();
      }

      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;

      const wantsText =
        textRef.current === true ||
        (textRef.current === "auto" && size >= 96);

      if (wantsText) {
        // On a dark ground the letters need something to sit on, or they float
        // over whatever strand happens to be behind them. The badge is only
        // drawn with the wordmark: at masthead size it would fill the hollow
        // and the mark would stop reading as a ring.
        if (addRef.current) {
          const c = size / 2;
          const badgeR = size * 0.2;
          ctx.globalCompositeOperation = "source-over";
          const badge = ctx.createRadialGradient(
            c, c - badgeR * 0.25, 0, c, c, badgeR
          );
          badge.addColorStop(0, "rgba(46, 33, 74, 0.97)");
          badge.addColorStop(0.62, "rgba(24, 17, 40, 0.94)");
          badge.addColorStop(1, "rgba(12, 9, 20, 0)");
          ctx.fillStyle = badge;
          ctx.beginPath();
          ctx.arc(c, c, badgeR, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalCompositeOperation = "lighter";
          ctx.strokeStyle = "rgba(168, 140, 235, 0.16)";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(c, c, badgeR * 0.94, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalCompositeOperation = "source-over";
        }
        if (!glyphs) glyphs = WORDMARK.paths.map((d) => new Path2D(d));
        const m = wordmarkTransform(size, 0.115);
        ctx.save();
        ctx.translate(m.tx, m.ty);
        ctx.scale(m.scale, m.scale);
        ctx.lineWidth = WORDMARK.strokeWidth;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.strokeStyle = monoRef.current
          ? `rgb(${inkRgb[0]},${inkRgb[1]},${inkRgb[2]})`
          : addRef.current
            ? "#F2F0FA"
            : WORDMARK_INK;
        for (const g of glyphs) ctx.stroke(g);
        ctx.restore();
      }
    };

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      size = Math.max(1, Math.round(Math.min(rect.width, rect.height)));
      // Assigning width/height wipes the bitmap and resets the transform, so a
      // frame has to be redrawn immediately or the masthead goes blank.
      canvas.width = Math.round(size * dpr);
      canvas.height = Math.round(size * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      paint(performance.now());
    };

    const start = performance.now();
    paint = render;
    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

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
    };
  }, []);

  return (
    <canvas
      ref={ref}
      className={mono ? `${className} mono` : className}
      role="img"
      aria-label="EUV Components Optimizer"
    />
  );
}

import { useEffect, useRef } from "react";

/**
 * Hero background — laser-produced-plasma source, rendered across the whole
 * section rather than boxed in a card.
 *
 * A tin droplet falls into the focus, a CO2 pulse vaporises it, the plasma
 * radiates 13.5 nm light into 4π steradians, and the collector gathers the one
 * cone it subtends and brings it to the intermediate focus. Everything
 * downstream of the IF — illuminator, reticle, mirror train, wafer — is
 * screen 9's beamline (SimFlow). This is the part before it.
 *
 * ---------------------------------------------------------------------------
 * Glow on a mint-green page
 *
 * The filaments are additive light. Over a pale ground there is no headroom to
 * add to, so `lighter` renders nothing — the same wall the logo hit, solved
 * there by going subtractive. Subtractive would work here too and would cost
 * the glow entirely, so instead the canvas paints its own pool: a wide radial
 * of deep green-black centred on the source, opaque under the optics and fully
 * transparent long before it reaches the text column.
 *
 * The pool is tinted green-black, not neutral. A neutral dark over a green page
 * reads as a grey bruise; matching the page's hue family makes it read as
 * depth. It is also pushed right, so the left of the section stays untouched
 * mint and the headline sits on flat colour at full contrast.
 *
 * ---------------------------------------------------------------------------
 * The telemetry is real
 *
 * Every readout comes from the run in memory: drive power, conversion
 * efficiency, collector capture, intermediate-focus power, printed half-pitch,
 * throughput. Change a constraint and the panel changes with it.
 *
 * The geometry is derived too. The collector's half-angle comes from inverting
 * the solid angle of a cone,
 *
 *     f = (1 - cos θ) / 2      ->      θ = acos(1 - 2f)
 *
 * so at 16.6% capture the rings open to 48° and the filaments that miss them
 * are genuinely the 83% a real source throws away. The capture dial's filled
 * sweep is the same number again, so the picture and the readout cannot
 * disagree.
 *
 * 13.5 nm is far outside the visible band, so the cyan/magenta palette is false
 * colour and the legend says so.
 */

const FILAMENTS = 34;
const FIL_STEPS = 16;

/* Fixed by the Mo/Si multilayer rather than by the optimiser, so it is a
   constant here and not a payload field. */
const LAMBDA_NM = 13.5;

export function PlasmaField({ data }) {
  const ref = useRef(null);
  const dataRef = useRef(data);
  dataRef.current = data;
  // Held so a data change can force a repaint from outside the mount effect.
  const paintRef = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")
      ?.matches;

    // Alpha is required now: the canvas sits over the page rather than over
    // its own opaque card, so everything outside the pool must composite
    // through to the mint ground.
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
      // Assigning width/height wipes the bitmap and resets the transform, so a
      // frame must be repainted immediately or the section goes blank.
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      paint(performance.now());
    };
    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    // ResizeObserver covers layout changes; this covers the viewport changing
    // without the element's box changing, which is what dragging the window
    // between monitors of different pixel ratios looks like.
    window.addEventListener("resize", resize);

    // Every moving part of this scene — the pulse cycle, the droplet, the
    // drive beam, the filament wobble, the core flicker, the sweep — is
    // driven off `t`, so scaling `t` alone slows the whole thing coherently
    // and keeps the timing relationships between them intact. Slowing the
    // parts individually would drift them out of step with each other.
    // At 0.45 the strike cycle drops from 1.1 Hz to about 0.5 Hz: roughly one
    // pulse every two seconds, calm enough to watch behind the headline.
    const SPEED = 0.45;

    // Offset so the very first frame lands mid-pulse. t=0 is between strikes —
    // and the first frame is the ONLY frame in a backgrounded or
    // non-compositing tab, the state a demo laptop sits in while you set up.
    // Dividing by SPEED keeps the opening frame identical at any speed: the
    // scaling below multiplies it straight back out to the same t of 0.690.
    const start = performance.now() - 690 / SPEED;

    const render = (now) => {
      const t = ((now - start) / 1000) * SPEED;
      const s = dataRef.current?.simulation || {};

      const capture = Math.min(
        0.9,
        Math.max(0.01, (s.collector_efficiency_pct ?? 16.6) / 100)
      );
      const half = Math.acos(1 - 2 * capture);

      // The scene lives in the right-hand portion; the left is left alone so
      // the headline sits on untouched mint.
      const narrow = w < 780;
      const cx = w * (narrow ? 0.5 : 0.67);
      const cy = h * 0.5;
      const scale = Math.min(w * 0.23, h * 0.66) * 0.5;
      const ifx = Math.min(w - scale * 0.5, cx + scale * 2.3);
      const R = scale * 1.06;

      const fs = Math.max(8.5, Math.min(12, w * 0.0092));
      ctx.font = `${fs}px "Cascadia Mono", "Consolas", ui-monospace, monospace`;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      // ---- the pool ----
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;
      // Sized to the scene and centred on it, not on the canvas. Sizing it
      // off the viewport made a radial big enough to reach the copy column,
      // and a wide soft dark gradient over a pale page does not read as depth
      // — it reads as a grey bruise. Deep and contained beats big and faint.
      const poolCx = narrow ? cx : (cx + ifx) / 2;
      const poolR = (ifx - cx) / 2 + R * 1.45;
      const poolRy = Math.min(poolR, h * 0.6);

      ctx.save();
      ctx.translate(poolCx, cy);
      ctx.scale(1, poolRy / poolR);
      const pool = ctx.createRadialGradient(0, 0, 0, 0, 0, poolR);
      // Holds near-full opacity across the scene, then falls off hard. The
      // long lazy ramp is what turned to smudge.
      pool.addColorStop(0, "rgba(5, 12, 10, 0.985)");
      pool.addColorStop(0.55, "rgba(6, 14, 11, 0.97)");
      pool.addColorStop(0.76, "rgba(9, 20, 16, 0.82)");
      pool.addColorStop(0.9, "rgba(14, 29, 23, 0.36)");
      pool.addColorStop(1, "rgba(20, 38, 30, 0)");
      ctx.fillStyle = pool;
      ctx.beginPath();
      ctx.arc(0, 0, poolR, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // Graticule, clipped to where the pool is dark enough to carry it.
      // Snapped to whole pixels so it stays a hairline.
      ctx.save();
      ctx.beginPath();
      // 0.62, not 0.8: past that the pool is under ~70% opaque and the
      // hairlines start showing on the mint outside the scene.
      ctx.ellipse(poolCx, cy, poolR * 0.62, poolRy * 0.62, 0, 0, Math.PI * 2);
      ctx.clip();
      ctx.strokeStyle = "rgba(130, 190, 165, 0.08)";
      ctx.lineWidth = 1;
      const step = Math.max(30, Math.round(scale * 0.4));
      ctx.beginPath();
      for (let x = cx % step; x < w; x += step) {
        ctx.moveTo(Math.round(x) + 0.5, 0);
        ctx.lineTo(Math.round(x) + 0.5, h);
      }
      for (let y = cy % step; y < h; y += step) {
        ctx.moveTo(0, Math.round(y) + 0.5);
        ctx.lineTo(w, Math.round(y) + 0.5);
      }
      ctx.stroke();
      ctx.restore();

      // ---- pulse timing ----
      // 50 kHz in a production source, slowed to ~1.1 Hz so a viewer can
      // resolve individual strikes. A real source never goes out between
      // droplets, so the envelope has a floor — which also means the section
      // is never caught dark on a static first frame.
      const phase = (t * 1.1) % 1;
      const strike =
        phase < 0.62 ? 0 : Math.pow(1 - (phase - 0.62) / 0.38, 2.2);
      const fire = Math.max(0.2, strike);
      const conv = Math.max(0, Math.min(1, (fire - 0.15) * 1.6));

      // ---- droplet ----
      if (phase < 0.62) {
        const dy = cy - scale * 1.45 + (scale * 1.45 + 5) * (phase / 0.62);
        ctx.fillStyle = "rgba(198, 216, 255, 0.9)";
        ctx.beginPath();
        ctx.arc(cx, dy, Math.max(1.5, scale * 0.02), 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalCompositeOperation = "lighter";

      // ---- CO2 drive pulse ----
      if (phase > 0.5 && phase < 0.72) {
        const k = (phase - 0.5) / 0.22;
        const x0 = cx - scale * 3.2;
        const head = x0 + (cx - x0) * k;
        const g = ctx.createLinearGradient(head - scale, 0, head, 0);
        g.addColorStop(0, "rgba(255, 96, 60, 0)");
        g.addColorStop(1, `rgba(255, 128, 74, ${0.5 * (1 - k * 0.3)})`);
        ctx.strokeStyle = g;
        ctx.lineWidth = Math.max(2, scale * 0.03);
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(Math.max(0, head - scale), cy);
        ctx.lineTo(head, cy);
        ctx.stroke();
      }

      // ---- plasma filaments ----
      // Curved, not radial: each wanders as it leaves the core, tight at the
      // centre and whipping at the tips. Cyan on the upper flank through blue
      // into magenta below.
      ctx.lineCap = "round";
      for (let i = 0; i < FILAMENTS; i++) {
        const base = (i / FILAMENTS) * Math.PI * 2;
        let d = Math.abs(base - Math.PI);
        if (d > Math.PI) d = Math.PI * 2 - d;
        const captured = d <= half;

        const reach = (captured ? R : scale * 2.6) * Math.min(1, fire * 2.1);
        if (reach < scale * 0.1) continue;

        const up = (Math.sin(base) + 1) / 2;
        const col = captured
          ? [110 + 60 * up, 210 - 40 * up, 255]
          : [200 - 120 * up, 90 + 90 * up, 235 + 20 * up];
        const a = (captured ? 0.55 : 0.2) * fire;

        ctx.strokeStyle = `rgba(${col[0] | 0}, ${col[1] | 0}, ${col[2] | 0}, ${a})`;
        ctx.lineWidth = captured ? 1.5 : 0.9;
        ctx.beginPath();
        for (let k = 0; k <= FIL_STEPS; k++) {
          const f = k / FIL_STEPS;
          const rr = reach * f;
          const wob =
            Math.sin(f * 5.5 + t * 3 + i * 1.7) * 0.055 * f +
            Math.sin(f * 11 - t * 1.9 + i) * 0.022 * f * f;
          const ang = base + wob;
          const x = cx + Math.cos(ang) * rr;
          const y = cy + Math.sin(ang) * rr;
          if (k === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // ---- concentric gold collector shells ----
      const RINGS = [
        { r: 1.0, w: 0.05, a: 0.95 },
        { r: 0.925, w: 0.026, a: 0.6 },
        { r: 0.862, w: 0.016, a: 0.4 },
      ];
      for (const ring of RINGS) {
        const rr = R * ring.r;
        const g = ctx.createLinearGradient(
          cx - rr, cy - rr, cx - rr * 0.2, cy + rr
        );
        g.addColorStop(0, `rgba(150, 104, 32, ${ring.a})`);
        g.addColorStop(0.42, `rgba(255, 214, 138, ${ring.a})`);
        g.addColorStop(0.6, `rgba(224, 163, 60, ${ring.a})`);
        g.addColorStop(1, `rgba(132, 92, 28, ${ring.a})`);
        ctx.strokeStyle = g;
        ctx.lineWidth = Math.max(1, scale * ring.w);
        ctx.lineCap = "butt";
        ctx.beginPath();
        ctx.arc(cx, cy, rr, Math.PI - half, Math.PI + half);
        ctx.stroke();
      }
      ctx.strokeStyle = `rgba(255, 236, 196, ${0.2 + 0.6 * fire})`;
      ctx.lineWidth = Math.max(1, scale * 0.012);
      ctx.beginPath();
      ctx.arc(cx, cy, R * 0.972, Math.PI - half, Math.PI + half);
      ctx.stroke();

      // Segment ticks — a real collector is a segmented optic.
      ctx.strokeStyle = "rgba(255, 214, 138, 0.34)";
      ctx.lineWidth = 1;
      for (let i = 0; i <= 10; i++) {
        const a = Math.PI - half + (i / 10) * half * 2;
        const ca = Math.cos(a);
        const sa = Math.sin(a);
        ctx.beginPath();
        ctx.moveTo(cx + ca * R * 0.845, cy + sa * R * 0.845);
        ctx.lineTo(cx + ca * R * 1.02, cy + sa * R * 1.02);
        ctx.stroke();
      }

      // ---- reflected cone -> intermediate focus ----
      if (conv > 0) {
        for (let i = 0; i <= 14; i++) {
          const a = Math.PI - half + (i / 14) * half * 2;
          const rx = cx + Math.cos(a) * R * 0.93;
          const ry = cy + Math.sin(a) * R * 0.93;
          ctx.strokeStyle = `rgba(240, 198, 120, ${0.4 * conv})`;
          ctx.lineWidth = 1.1;
          ctx.beginPath();
          ctx.moveTo(rx, ry);
          ctx.lineTo(rx + (ifx - rx) * conv, ry + (cy - ry) * conv);
          ctx.stroke();
        }
      }

      // ---- the plasma core ----
      const flick = 0.84 + Math.sin(t * 31) * 0.1 + Math.sin(t * 67) * 0.06;
      const coreR = scale * (0.045 + 0.15 * fire) * flick;
      const cg = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR * 3.2);
      cg.addColorStop(0, `rgba(255, 255, 253, ${0.95 * Math.max(0.25, fire)})`);
      cg.addColorStop(0.14, `rgba(190, 245, 255, ${0.72 * fire})`);
      cg.addColorStop(0.38, `rgba(150, 130, 255, ${0.4 * fire})`);
      cg.addColorStop(0.68, `rgba(226, 80, 200, ${0.2 * fire})`);
      cg.addColorStop(1, "rgba(120, 60, 200, 0)");
      ctx.fillStyle = cg;
      ctx.beginPath();
      ctx.arc(cx, cy, coreR * 3.2, 0, Math.PI * 2);
      ctx.fill();

      // ---- intermediate focus ----
      const ig = ctx.createRadialGradient(ifx, cy, 0, ifx, cy, scale * 0.32);
      ig.addColorStop(0, `rgba(255, 218, 150, ${0.25 + 0.7 * conv})`);
      ig.addColorStop(1, "rgba(224, 163, 60, 0)");
      ctx.fillStyle = ig;
      ctx.beginPath();
      ctx.arc(ifx, cy, scale * 0.32, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#ffe9bd";
      ctx.beginPath();
      ctx.arc(ifx, cy, Math.max(1.6, scale * 0.026), 0, Math.PI * 2);
      ctx.fill();

      /* ------------------------------------------------------------------
         HUD

         Everything here is placed relative to the SCENE, not to the canvas
         edges. The canvas now spans the whole section, and a readout pinned
         to its top-left corner would land in the middle of the headline.
         ------------------------------------------------------------------ */
      ctx.globalCompositeOperation = "source-over";
      const INK = "rgba(216, 236, 228, 0.92)";
      const DIM = "rgba(150, 196, 178, 0.68)";
      const GOLD = "rgba(246, 206, 140, 0.95)";

      // Reticle on the source.
      const ret = coreR * 3.4 + scale * 0.1;
      ctx.strokeStyle = "rgba(170, 220, 200, 0.45)";
      ctx.lineWidth = 1;
      for (let q = 0; q < 4; q++) {
        const a0 = q * (Math.PI / 2) + 0.24;
        ctx.beginPath();
        ctx.arc(cx, cy, ret, a0, a0 + Math.PI / 2 - 0.48);
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.moveTo(cx - ret * 1.32, cy);
      ctx.lineTo(cx - ret * 1.06, cy);
      ctx.moveTo(cx + ret * 1.06, cy);
      ctx.lineTo(cx + ret * 1.32, cy);
      ctx.stroke();

      // Optic labels.
      ctx.textAlign = "center";
      ctx.fillStyle = GOLD;
      ctx.fillText("COLLECTOR", cx - R * 0.6, cy + R * 1.05);
      ctx.fillText("IF", ifx, cy - scale * 0.46);
      ctx.fillStyle = INK;
      ctx.fillText("Sn PLASMA", cx, cy + ret + fs * 1.7);

      // The numeric readouts used to be drawn here. They are in the DOM now
      // (see the telemetry pill in Home.jsx): canvas text does not scale with
      // browser zoom, cannot be selected, and is invisible to a screen reader.
      // Moving them also ended a losing fight for horizontal space against the
      // copy column.

      // The capture dial used to sit here. It is gone: the telemetry pill
      // already shows COLLECTOR as a number, and the dial's caption landed
      // low enough that the pool had faded under it, leaving pale green text
      // on a pale green ground. Duplicated information is not worth a
      // contrast failure.

      // Scan sweep — the tell of a live instrument. Clipped to the pool so it
      // never washes across the copy.
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(poolCx, cy, poolR * 0.66, poolRy * 0.66, 0, 0, Math.PI * 2);
      ctx.clip();
      const sweepX = poolCx - poolR * 0.66 + ((t * 0.16) % 1) * poolR * 1.32;
      const sg = ctx.createLinearGradient(sweepX - fs * 5, 0, sweepX + fs * 5, 0);
      sg.addColorStop(0, "rgba(150, 230, 205, 0)");
      sg.addColorStop(0.5, "rgba(150, 230, 205, 0.05)");
      sg.addColorStop(1, "rgba(150, 230, 205, 0)");
      ctx.fillStyle = sg;
      ctx.fillRect(sweepX - fs * 5, 0, fs * 10, h);
      ctx.restore();
    };

    paint = render;
    paintRef.current = render;

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
      paintRef.current = null;
    };
  }, []);

  /* Repaint when the run changes.
   *
   * The animation loop would pick new numbers up on its next frame, but there
   * is no loop under `prefers-reduced-motion` — the readouts would sit on "—"
   * forever for anyone who has it set. The same gap shows up in any tab that
   * is not compositing: mount and resize both paint before /api/run answers,
   * and nothing repaints afterwards. */
  useEffect(() => {
    paintRef.current?.(performance.now());
  }, [data]);

  return <canvas className="hero-field" ref={ref} aria-hidden="true" />;
}

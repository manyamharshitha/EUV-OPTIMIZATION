/**
 * Orb mark — geometry, palette and letterforms.
 *
 * One source of truth for a shape that has to exist in four places: the live
 * canvas in the masthead, public/logo.svg, public/logo-mono.svg and
 * public/favicon.svg. The three .svg files are *generated* from this module by
 * tools/gen-logo.mjs (`npm run logo`), so the drawing cannot drift between the
 * app and the files handed to anyone outside it. Change the geometry here and
 * regenerate; do not hand-edit the .svg files.
 *
 * ---------------------------------------------------------------------------
 * The shape
 *
 * A tangle of great circles on a sphere, seen in orthographic projection. Each
 * strand has its own axis; the axes precess at different rates, so the ribbons
 * slide across one another instead of rotating as a rigid body. Two details do
 * most of the work:
 *
 *   - The centre is held open. A shell of curves seen from outside piles up at
 *     its silhouette and thins across the middle, so the alpha of every sample
 *     is faded by its distance from the centre of the projection. Without it
 *     the ribbons slash through the middle, the thing reads as an atom
 *     diagram, and nothing can live in the hollow.
 *
 *   - Axis pitch is kept out of a band around pi/2. A great circle whose plane
 *     contains the view axis projects to a straight line — a hard bright bar
 *     across the mark. Here |cos(beta)| >= ~0.31, so the flattest strand still
 *     projects to an ellipse a third as tall as it is wide.
 *
 * ---------------------------------------------------------------------------
 * Neon on white
 *
 * The reference is additive light on black. Additive light does not exist on
 * white: `lighter` over a white ground bleaches to nothing, and faking the
 * black ground under the orb leaves a grey halo where it feathers out. The
 * translation that does work is subtractive — saturated colour at low alpha,
 * composited with `multiply`, so every crossing *deepens* instead of blowing
 * out. Density builds where ribbons pile up, which is the same information the
 * additive version carries, inverted.
 *
 * Each ribbon is therefore four coincident strokes, not one — see PASS below:
 * `glow` and `haze` are the translucent energy field, `mid` is the body of the
 * ribbon and `core` is the hairline that gives it an edge. Two wide passes
 * rather than one, because a single wide stroke has a hard boundary and a
 * ribbon with a hard boundary reads as a pipe.
 *
 * There is also an optional `spec` pass — a pale hairline drawn *over* the
 * core with normal compositing, on the frontmost segments only. That is the
 * one honest stand-in for the reference's hot white crossings: on white you
 * cannot make a highlight brighter than the paper, so the highlight becomes a
 * specular streak down the ribbon instead. Under this inversion the brightest
 * thing in the reference maps to the *darkest, most saturated* thing here.
 * That is a real difference from the source image, not a defect in the
 * translation, and no amount of tuning removes it.
 *
 * ---------------------------------------------------------------------------
 * Why runs rather than per-segment strokes
 *
 * Alpha, colour and width all vary continuously along a strand, but stroking
 * segment by segment with round caps beads at every join. So each strand is
 * quantised into style buckets and emitted as continuous *runs* that share
 * their endpoints and use butt caps. The steps are below the visible threshold
 * at these alphas; the beading is not.
 */

const TAU = Math.PI * 2;

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

const smoothstep = (e0, e1, x) => {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
};

/* --------------------------------------------------------------------------
   Palette

   Sampled off the reference: hot pink through magenta and violet into indigo
   and electric blue, with a cyan tip. Every stop is saturated and mid-dark —
   pale colours vanish under `multiply`, and near-black ones stop reading as
   light. Hue is driven by horizontal position, which is what puts magenta on
   one flank and blue on the other the way the reference does.
   -------------------------------------------------------------------------- */
const STOPS = [
  [0.0, 255, 61, 168],
  [0.2, 228, 56, 205],
  [0.42, 158, 58, 240],
  [0.66, 92, 70, 246],
  [0.86, 46, 122, 255],
  [1.0, 56, 190, 255],
];

export function ramp(t) {
  t = clamp(t, 0, 1);
  let i = 1;
  while (i < STOPS.length - 1 && t > STOPS[i][0]) i++;
  const a = STOPS[i - 1];
  const b = STOPS[i];
  const span = b[0] - a[0];
  const k = span === 0 ? 0 : (t - a[0]) / span;
  return [
    a[1] + (b[1] - a[1]) * k,
    a[2] + (b[2] - a[2]) * k,
    a[3] + (b[3] - a[3]) * k,
  ];
}

const toward = (rgb, to, k) => [
  rgb[0] + (to[0] - rgb[0]) * k,
  rgb[1] + (to[1] - rgb[1]) * k,
  rgb[2] + (to[2] - rgb[2]) * k,
];

const WHITE = [255, 255, 255];

/* The ground a dark-mode caller composites onto. Far strands wash toward this
   instead of toward white — see the `dark` option on orbRuns. */
const VOID = [9, 8, 16];

export function hex(rgb) {
  const h = (v) => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, "0");
  return `#${h(rgb[0])}${h(rgb[1])}${h(rgb[2])}`;
}

/* Deterministic PRNG. The mark must be byte-identical in the app, in the
   generated .svg files and between two people's screens, so nothing here is
   allowed to touch Math.random. */
function lcg(seed) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/**
 * Strand parameters. `beta0` is the polar angle of the strand's axis measured
 * from the view direction; it is confined to [0.44, 1.10] (or its mirror in
 * the far hemisphere) and wobbles by at most +/-0.15, which keeps |cos(beta)|
 * above ~0.31 and every strand safely elliptical.
 */
export function makeStrands(count, seed = 0x5eed) {
  const rnd = lcg(seed);
  const out = [];
  for (let i = 0; i < count; i++) {
    const far = i % 2 === 1;
    const beta = 0.44 + rnd() * 0.66;
    out.push({
      beta0: far ? Math.PI - beta : beta,
      alpha0: rnd() * TAU,
      wAz: (0.03 + rnd() * 0.075) * (rnd() < 0.5 ? -1 : 1),
      wPol: 0.017 + rnd() * 0.05,
      bAmp: 0.06 + rnd() * 0.09,
      k1: 2 + Math.floor(rnd() * 3),
      k2: 3 + Math.floor(rnd() * 4),
      k3: 2 + Math.floor(rnd() * 3),
      k4: 1 + Math.floor(rnd() * 2),
      a1: 0.05 + rnd() * 0.085,
      a2: 0.028 + rnd() * 0.045,
      b1: 0.008 + rnd() * 0.022,
      ph1: rnd() * TAU,
      ph2: rnd() * TAU,
      ph3: rnd() * TAU,
      ph4: rnd() * TAU,
      hueOff: (rnd() - 0.5) * 0.24,
      weight: 0.55 + rnd() * 1.75,
      dim: 0.8 + rnd() * 0.35,
    });
  }
  return out;
}

/* Four coincident strokes make one ribbon. The widths are fractions of the
   orb radius; the alphas are what turns overlap into density.

   `glow` and `haze` together give the soft edge — a single wide stroke has a
   hard boundary, and a ribbon with a hard boundary reads as a pipe. `wf`
   scales the minimum width, so a pass that is meant to be broad does not
   collapse onto the same one pixel as the core at small sizes. */
const PASS = {
  //        width     alpha   min-w  lighten  cap
  glow: { w: 0.13, a: 0.17, wf: 2.6, light: 0.14, op: "multiply", cap: "round" },
  haze: { w: 0.058, a: 0.38, wf: 1.7, light: 0.1, op: "multiply", cap: "round" },
  mid: { w: 0.021, a: 0.55, wf: 1.15, light: 0.04, op: "multiply", cap: "butt" },
  core: { w: 0.007, a: 1.0, wf: 1.0, light: 0.0, op: "multiply", cap: "butt" },
  spec: { w: 0.0026, a: 0.5, wf: 0.8, light: 0.68, op: "source-over", cap: "butt" },
};

/**
 * Build the mark as a list of strokable runs, in a `size` x `size` box.
 *
 * Returns `[{ pts, color, alpha, width, op, depth }]` where `pts` is a flat
 * [x0, y0, x1, y1, ...] array. Consumers stroke them in order: canvas with
 * globalAlpha + globalCompositeOperation, the SVG generator with
 * stroke-opacity + mix-blend-mode.
 */
export function orbRuns({
  size = 512,
  time = 0,
  count = 14,
  samples = 132,
  passes = ["glow", "haze", "mid", "core", "spec"],
  holeIn = 0.46,
  holeOut = 0.8,
  envAmt = 0.5,
  radiusScale = 0.445,
  minWidth = 1,
  gain = 1,
  cut = 0.016,
  quantA = 9,
  quantC = 10,
  quantD = 4,
  mono = null,
  precision = 2,
  /* Set when the caller composites additively over a dark ground. Depth has
     to reverse: on paper the far side of the sphere recedes by washing toward
     the page, but over black that same wash makes the BACK of the sphere the
     brightest thing in the picture. */
  dark = false,
} = {}) {
  const cx = size / 2;
  const cy = size / 2;
  const R = size * radiusScale;
  const strands = makeStrands(count);

  // A fixed tilt about the horizontal axis. Purely compositional: it stops the
  // ellipse family from sharing one horizon line.
  const TILT = 0.2;
  const ct = Math.cos(TILT);
  const st = Math.sin(TILT);

  const q = precision === 0 ? 1 : Math.pow(10, precision);
  const snap = (v) => Math.round(v * q) / q;

  const out = [];

  for (const s of strands) {
    // --- axis for this instant -------------------------------------------
    const beta = s.beta0 + s.bAmp * Math.sin(time * s.wPol + s.ph1);
    const az = s.alpha0 + time * s.wAz;
    const sb = Math.sin(beta);
    const cb = Math.cos(beta);
    const nx = sb * Math.cos(az);
    const ny = sb * Math.sin(az);
    const nz = cb;
    // u = normalise(n x z), v = n x u. |sb| >= sin(0.29) so u is never
    // degenerate, and |cb| >= 0.31 so the circle never projects to a line.
    const ux = ny / sb;
    const uy = -nx / sb;
    const vx = (cb * nx) / sb;
    const vy = (cb * ny) / sb;
    const vz = -sb;

    // --- sample the strand -------------------------------------------------
    const P = new Array(samples + 1);
    for (let i = 0; i <= samples; i++) {
      const th = (i / samples) * TAU;

      // Out-of-plane displacement: what turns an orbit into a ribbon.
      const w =
        s.a1 * Math.sin(s.k1 * th + s.ph1 + time * 0.31) +
        s.a2 * Math.sin(s.k2 * th - s.ph2 - time * 0.23);

      const c = Math.cos(th);
      const sn = Math.sin(th);
      let dx = c * ux + sn * vx + w * nx;
      let dy = c * uy + sn * vy + w * ny;
      let dz = sn * vz + w * nz; // uz is 0 by construction

      // Renormalise so the displacement rides on the sphere rather than
      // bulging off it — the silhouette has to stay circular.
      const rho = (1 + s.b1 * Math.sin(s.k3 * th + s.ph3 + time * 0.19)) /
        Math.hypot(dx, dy, dz);
      dx *= rho;
      dy *= rho;
      dz *= rho;

      const ty = dy * ct - dz * st;
      const tz = dy * st + dz * ct;

      const rr = Math.hypot(dx, ty);
      const depth = 0.5 + 0.5 * clamp(tz, -1, 1); // 0 back, 1 front

      // Hollow centre, silhouette pile-up, and front-weighting.
      const hole = smoothstep(holeIn, holeOut, rr);
      const rim = 0.7 + 0.3 * smoothstep(0.62, 1.0, rr);
      const front = 0.55 + 0.45 * depth;
      // Envelope along the strand: each ribbon fades in and out around its
      // loop rather than being a closed hoop of constant weight. This is what
      // makes the tangle read as trailing silk instead of as wireframe.
      const env =
        1 -
        envAmt * (0.5 - 0.5 * Math.sin(s.k4 * th + s.ph4 + time * 0.27));

      const ht = clamp(
        0.48 + 0.46 * dx + 0.1 * ty + 0.1 * (depth - 0.5) + s.hueOff,
        0,
        1
      );

      P[i] = {
        x: cx + dx * R,
        y: cy - ty * R,
        a: hole * rim * front * env * s.dim,
        ht,
        depth,
      };
    }

    // --- split into runs ---------------------------------------------------
    for (const name of passes) {
      const cfg = PASS[name];
      if (!cfg) continue;
      const runs = [];
      let cur = null;
      let prevLive = false;

      for (let i = 0; i <= samples; i++) {
        const p = P[i];
        // p.a is a product of five 0..1 factors, so it collapses toward zero
        // fast. The exponent lifts the mid-range back up: without it the whole
        // mark sits at a tenth of the intended density and reads as wire.
        const shade = Math.pow(p.a, 0.5);
        const alpha =
          name === "spec"
            ? cfg.a * shade * smoothstep(0.8, 1.0, p.depth) * gain
            : cfg.a * shade * gain;

        if (alpha < cut) {
          cur = null;
          prevLive = false;
          continue;
        }

        // Never round down to zero: a run that survived `cut` must still be
        // drawn, or a coarse bucket count silently deletes whole ribbons.
        const aB = Math.max(
          1,
          Math.round(clamp(alpha / (cfg.a * gain), 0, 1) * quantA)
        );
        const cB = Math.round(p.ht * quantC);
        const dB = Math.round(p.depth * quantD);
        const key = `${aB}|${cB}|${dB}`;

        if (!cur || cur.key !== key) {
          const prev = cur;
          const dq = dB / quantD;
          const width = Math.max(
            minWidth * cfg.wf,
            cfg.w * R * s.weight * (0.55 + 0.45 * dq)
          );
          let rgb;
          if (mono) {
            rgb = mono;
          } else {
            rgb = ramp(cB / quantC);
            if (dark) {
              // Recede into the ground, not out of it.
              rgb = toward(rgb, VOID, 0.52 * (1 - dq));
              // The specular pass is a highlight and still lifts toward white;
              // the wide passes do not, or the glow turns milky.
              if (name === "spec") rgb = toward(rgb, WHITE, cfg.light);
            } else {
              // Far-side strands wash toward the paper, so the tangle reads as
              // a volume rather than as a flat knot.
              rgb = toward(rgb, WHITE, 0.26 * (1 - dq));
              if (cfg.light) rgb = toward(rgb, WHITE, cfg.light);
            }
          }
          cur = {
            key,
            pass: name,
            pts: [],
            color: hex(rgb),
            alpha:
              Math.round(Math.min(1, (aB / quantA) * cfg.a * gain) * 1000) / 1000,
            width: Math.round(width * 100) / 100,
            op: cfg.op,
            // Butt caps on the hairlines, because runs abut and a round cap
            // would bead at every style change. Round caps on the wide
            // passes, because a 40px-wide stroke stopped flat leaves a
            // straight edge in mid-air and the mark grows visible rectangles.
            cap: cfg.cap,
            depth: dq,
          };
          // Share the endpoint with the previous run so butt caps abut
          // instead of leaving a hairline gap.
          if (prev && prevLive) {
            cur.pts.push(prev.pts[prev.pts.length - 2], prev.pts[prev.pts.length - 1]);
          }
          runs.push(cur);
        }
        cur.pts.push(snap(p.x), snap(p.y));
        prevLive = true;
      }

      // The strand is a closed loop; if the styles match across theta = 0 the
      // first and last runs are one run with a seam in it.
      if (runs.length > 1) {
        const first = runs[0];
        const last = runs[runs.length - 1];
        if (first.key === last.key && first.pts[0] === last.pts[last.pts.length - 2]) {
          last.pts.push(first.pts[2] ?? first.pts[0], first.pts[3] ?? first.pts[1]);
        }
      }

      for (const r of runs) {
        if (r.pts.length >= 4) out.push(r);
      }
    }
  }

  // Pass by pass, and back to front within a pass, so the near ribbons finish
  // on top. `multiply` is commutative in colour but not once partial alpha is
  // involved, so the order is not cosmetic.
  const rank = new Map(passes.map((p, i) => [p, i]));
  out.sort((a, b) => {
    const d = rank.get(a.pass) - rank.get(b.pass);
    return d !== 0 ? d : a.depth - b.depth;
  });

  return out;
}

/* --------------------------------------------------------------------------
   The wordmark

   "euv", monoline geometric sans, drawn as three stroked paths rather than as
   set type. A logo cannot depend on a font being installed, and this project
   cannot ship a webfont — demo_proof.py certifies the bundle runs with the
   network pulled, so the letterforms have to be geometry.

   Local coordinates: baseline at y = 0, x-height top at y = -100, stroke
   width 13, round caps and joins. Including the stroke the artwork occupies
   x [0, 332], y [-106.5, 6.5].
   -------------------------------------------------------------------------- */
export const WORDMARK = {
  strokeWidth: 13,
  box: { x: 0, y: -106.5, w: 332, h: 113 },
  paths: [
    // e — crossbar, then one continuous arc up over the top, round the left
    // and under the bottom, opening at about 38 degrees below the right.
    "M6.68,-54 H93.32 A43.5,43.5 0 1 0 84.28,-23.23",
    // u — two stems and a semicircular bowl, no spur.
    "M132.5,-100 V-38.5 A38.5,38.5 0 0 0 209.5,-38.5 V-100",
    // v — two diagonals; the round join makes the apex.
    "M248.5,-100 L287,-8 L325.5,-100",
  ],
};

/** Deep violet-black. Reads as ink, but is tinted toward the orb's palette. */
export const WORDMARK_INK = "#1f1440";

/**
 * Placement of the wordmark inside a `size` box: scaled so its height is
 * `heightFrac` of the box and its optical centre sits on the box centre.
 */
export function wordmarkTransform(size, heightFrac = 0.11) {
  const scale = (size * heightFrac) / WORDMARK.box.h;
  const cx = WORDMARK.box.x + WORDMARK.box.w / 2;
  const cy = WORDMARK.box.y + WORDMARK.box.h / 2;
  return {
    scale,
    tx: size / 2 - cx * scale,
    ty: size / 2 - cy * scale,
    strokeWidth: WORDMARK.strokeWidth * scale,
  };
}

/**
 * Regenerates public/logo.svg, logo-mono.svg and favicon.svg from
 * src/lib/orb.js.  Run with `npm run logo`.
 *
 * The three files are build artefacts, not artwork anyone should hand-edit.
 * They exist because the mark has to be handed to people who are not running
 * this app — a README, a slide, a browser tab — and the only way to stop those
 * copies drifting from the live one is to derive them from the same module the
 * canvas uses.
 *
 * Node only, at author time. Nothing here ships in the bundle, so the offline
 * claim demo_proof.py certifies is untouched.
 *
 * POSE is the instant of the animation the still files freeze. Changing it
 * redraws all three; keep it fixed unless the mark is being redesigned.
 */
import { writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const orb = await import(pathToFileURL(join(WEB, "src/lib/orb.js")).href);
const { orbRuns, WORDMARK, WORDMARK_INK, wordmarkTransform } = orb;

const POSE = Number(process.env.POSE ?? 3.1);

function d(run) {
  const p = run.pts;
  let s = `M${p[0]} ${p[1]}`;
  for (let i = 2; i < p.length; i += 2) s += ` ${p[i]} ${p[i + 1]}`;
  return s;
}

/* Runs that share a style become one <path> with several subpaths. Without
   this the attribute block is three quarters of the file. Merging happens
   inside a pass only, so the pass order — which multiply depends on — holds. */
function body(runs, { mono }) {
  const out = [];
  let op = null;
  let bucket = new Map();

  const flush = () => {
    for (const [, v] of bucket) {
      const stroke = mono ? "currentColor" : v.color;
      out.push(
        `    <path d="${v.d.join("")}" stroke="${stroke}" stroke-opacity="${v.alpha}" stroke-width="${v.width}"/>`
      );
    }
    bucket = new Map();
  };

  for (const r of runs) {
    const gk = `${r.op}|${r.cap}`;
    if (gk !== op) {
      if (op !== null) {
        flush();
        out.push("  </g>");
      }
      op = gk;
      const blend = r.op === "multiply" ? ' style="mix-blend-mode:multiply"' : "";
      out.push(`  <g${blend} fill="none" stroke-linecap="${r.cap}" stroke-linejoin="round">`);
    }
    const key = mono ? `${r.alpha}/${r.width}` : `${r.color}/${r.alpha}/${r.width}`;
    let v = bucket.get(key);
    if (!v) {
      v = { color: r.color, alpha: r.alpha, width: r.width, d: [] };
      bucket.set(key, v);
    }
    v.d.push(d(r));
  }
  if (op !== null) {
    flush();
    out.push("  </g>");
  }
  return out.join("\n");
}

/* One orbRuns call per pass, so each pass gets quantisation suited to it: the
   haze is a diffuse field and needs almost no colour resolution, the core is
   the drawing and needs all of it. */
function build(base, spec) {
  const all = [];
  for (const [name, q] of Object.entries(spec)) {
    all.push(...orbRuns({ ...base, ...q, passes: [name] }));
  }
  return all;
}

function wordmark(size, ink, heightFrac = 0.115) {
  const m = wordmarkTransform(size, heightFrac);
  const paths = WORDMARK.paths
    .map((p) => `      <path d="${p}"/>`)
    .join("\n");
  return `  <g transform="translate(${m.tx.toFixed(2)} ${m.ty.toFixed(2)}) scale(${m.scale.toFixed(5)})"
     fill="none" stroke="${ink}" stroke-width="${WORDMARK.strokeWidth}"
     stroke-linecap="round" stroke-linejoin="round">
${paths}
  </g>`;
}

/* ---- logo.svg ----------------------------------------------------------- */
const logoRuns = build(
  { size: 512, time: POSE, count: 17, samples: 132, gain: 1, minWidth: 0.6, precision: 1 },
  {
    glow: { quantA: 2, quantC: 3, quantD: 2, cut: 0.02, samples: 72 },
    haze: { quantA: 4, quantC: 5, quantD: 2, cut: 0.03, samples: 96 },
    mid: { quantA: 6, quantC: 7, quantD: 3, cut: 0.03 },
    core: { quantA: 8, quantC: 9, quantD: 4, cut: 0.03 },
    spec: { quantA: 5, quantC: 5, quantD: 3, cut: 0.05 },
  }
);

const logo = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-labelledby="euvOrbTitle">
  <title id="euvOrbTitle">EUV Components Optimizer</title>
  <!-- Generated from web/src/lib/orb.js. Do not hand-edit: regenerate.

       Great circles on a sphere with precessing axes, drawn subtractively.
       The reference this comes from is additive light on black; on white
       there is no headroom to add to, so every ribbon is a wide low-alpha
       haze plus a hairline core, composited with multiply. Crossings deepen
       and saturate instead of bleaching out, which is what glowing silk
       actually looks like on paper.

       The white plate is part of the artwork, not a convenience: multiply is
       only defined against a ground, and the brief specifies a pure white
       one. For a transparent lockup use logo-mono.svg.

       This is the large cut. It carries the wordmark and is meant for 128px
       and up; below that use favicon.svg. -->
  <rect width="512" height="512" fill="#ffffff"/>
${body(logoRuns, { mono: false })}
${wordmark(512, WORDMARK_INK)}
</svg>
`;

/* ---- logo-mono.svg ------------------------------------------------------ */
const monoRuns = build(
  {
    size: 512,
    time: POSE,
    count: 11,
    samples: 132,
    gain: 0.78,
    minWidth: 0.6,
    precision: 1,
    mono: [0, 0, 0],
  },
  {
    glow: { quantA: 2, quantC: 1, quantD: 2, cut: 0.02, samples: 72 },
    haze: { quantA: 4, quantC: 1, quantD: 2, cut: 0.032, samples: 96 },
    mid: { quantA: 6, quantC: 1, quantD: 3, cut: 0.035 },
    core: { quantA: 8, quantC: 1, quantD: 4, cut: 0.035 },
  }
);

const mono = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-labelledby="euvOrbMonoTitle">
  <title id="euvOrbMonoTitle">EUV Components Optimizer</title>
  <!-- Generated from web/src/lib/orb.js. Do not hand-edit: regenerate.

       Single-plate cut. Every stroke is currentColor and only the opacity
       structure survives, so the same file inverts for a dark ground, prints
       as one plate, and drops into a stamp or an engraving without editing.
       Viewed on its own it falls back to black, which is the right default
       for a one-colour mark.

       No white plate and no blend modes here: the ground is unknown, and
       multiply against an unknown ground is not a mark, it is a gamble. The
       specular pass is dropped for the same reason — "paler than the ink" is
       meaningless when the ink might be the light one. -->
  <g color="#0f1115">
${body(monoRuns, { mono: true })}
${wordmark(512, "currentColor")}
  </g>
</svg>
`;

/* ---- favicon.svg -------------------------------------------------------- */
const favRuns = build(
  {
    size: 64,
    time: POSE,
    count: 8,
    samples: 96,
    gain: 1.3,
    minWidth: 3.8,
    holeIn: 0.46,
    holeOut: 0.78,
    // Almost no envelope: at this size a ribbon that fades out mid-loop is
    // just a chunk missing from the ring, and the mark stops being a sphere.
    envAmt: 0.1,
    radiusScale: 0.44,
    precision: 2,
  },
  {
    core: { quantA: 7, quantC: 9, quantD: 3, cut: 0.12 },
  }
);

const fav = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="EUV Components Optimizer">
  <!-- Generated from web/src/lib/orb.js. Do not hand-edit: regenerate.

       Favicon cut, and deliberately NOT logo.svg scaled down. Six strands
       instead of fifteen, no haze and no specular, and the stroke floored at
       4.2 units on a 64 grid so it still lands on a whole pixel at 16px. The
       wordmark is dropped: at 16px "euv" would be four pixels wide.

       Transparent, and no blend modes, so it survives a dark browser chrome
       and the various rasterisers that handle SVG favicons. -->
${body(favRuns, { mono: false })}
</svg>
`;

writeFileSync(join(WEB, "public/logo.svg"), logo);
writeFileSync(join(WEB, "public/logo-mono.svg"), mono);
writeFileSync(join(WEB, "public/favicon.svg"), fav);

const kb = (s) => (Buffer.byteLength(s) / 1024).toFixed(1) + " KB";
console.log("logo.svg      ", kb(logo), logoRuns.length, "runs");
console.log("logo-mono.svg ", kb(mono), monoRuns.length, "runs");
console.log("favicon.svg   ", kb(fav), favRuns.length, "runs");

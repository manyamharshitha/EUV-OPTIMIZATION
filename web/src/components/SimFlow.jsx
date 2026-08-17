import { useEffect, useRef } from "react";

/**
 * Animated EUV beamline — a Monte Carlo of the run's own photon budget.
 *
 * Left to right: a CO2 pulse strikes a tin droplet, the plasma radiates into
 * 4π, the collector gathers one slice to the intermediate focus, the beam
 * walks a fold-mirror train through the reticle, and what survives exposes the
 * wafer.
 *
 * Every probability comes from the backend payload. Nothing is tuned for
 * looks:
 *
 *   - a photon leaving the plasma enters the train with probability
 *     collector_efficiency_pct,
 *   - each mirror reflects it with probability mirror_reflectivity_pct,
 *   - the reticle-and-filter gate carries the remaining factor, derived as
 *     optical_transmission / reflectivity^mirrors so it stays exact without
 *     duplicating euv_simulation.py's MASK_REFLECTIVITY and SPF_TRANSMISSION
 *     constants here — if those change, this follows.
 *
 * So the arrival rate at the wafer converges on the analytic transmission by
 * construction rather than by assertion, and the counter under the canvas
 * shows the sampled figure next to the computed one. They should agree.
 *
 * That is the argument the screen exists to make: you watch photons stream out
 * of the focus and a trickle arrive. A ~99% mirror-train loss stops being a
 * table row.
 *
 * The spawn rate is the only free parameter, and it is deliberately high — a
 * faster Monte Carlo, not better odds. Raising the per-photon probabilities to
 * populate the beamline would have made the picture a lie.
 *
 * Canvas, not SVG/CSS: a Bernoulli trial per photon per bounce cannot be
 * keyframed. No library — third-party runtime code would break the offline
 * claim demo_proof.py certifies.
 */
export function SimFlow({ sim }) {
  const ref = useRef(null);
  const simRef = useRef(sim);
  simRef.current = sim;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)")
      ?.matches;

    const ctx = canvas.getContext("2d", { alpha: false });
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

    const photons = [];
    const flashes = [];
    const tally = { emitted: 0, captured: 0, printed: 0 };
    let spawnDebt = 0;
    let last = performance.now();
    const start = performance.now();

    const render = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const t = (now - start) / 1000;

      const s = simRef.current || {};
      const mirrors = Math.max(1, s.mirror_count || 10);
      const refl = Math.min(0.999, (s.mirror_reflectivity_pct ?? 70) / 100);
      const capture = (s.collector_efficiency_pct ?? 16.6) / 100;
      // Everything in the optical train that is not a fold mirror: reticle
      // reflectivity and the spectral purity filter, backed out of the
      // analytic figure so there is one source of truth.
      const trainTotal = (s.optical_transmission_pct ?? 1.3) / 100;
      const maskGate = Math.min(1, trainTotal / Math.pow(refl, mirrors));

      // ---- layout ----
      const srcX = w * 0.12;
      const beamY = h * 0.46;
      const ifX = w * 0.27;
      const trainX0 = w * 0.34;
      const trainX1 = w * 0.82;
      const waferX = w * 0.91;
      const topY = h * 0.32;
      const botY = h * 0.68;
      const maskAt = Math.ceil(mirrors / 2); // reticle sits mid-train

      const nodes = [];
      for (let i = 0; i < mirrors; i++) {
        const f = mirrors === 1 ? 0.5 : i / (mirrors - 1);
        nodes.push({
          kind: "mirror",
          x: trainX0 + (trainX1 - trainX0) * f,
          y: i % 2 === 0 ? topY : botY,
        });
      }
      nodes.splice(maskAt, 0, {
        kind: "mask",
        x: trainX0 + (trainX1 - trainX0) * ((maskAt - 0.5) / Math.max(1, mirrors - 1)),
        // Clear of the transmission readout printed along the top edge.
        y: h * 0.15,
      });

      // ---- ground ----
      ctx.globalCompositeOperation = "source-over";
      const ground = ctx.createLinearGradient(0, 0, 0, h);
      // Cream, not white: the page has no white in it anywhere.
      ground.addColorStop(0, "#f1e9e1");
      ground.addColorStop(1, "#e6e2e6");
      ctx.fillStyle = ground;
      ctx.fillRect(0, 0, w, h);

      // ---- beamline skeleton ----
      ctx.strokeStyle = "rgba(41, 35, 65, 0.10)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(ifX, beamY);
      nodes.forEach((n) => ctx.lineTo(n.x, n.y));
      ctx.lineTo(waferX - 22, beamY);
      ctx.stroke();

      // ---- CO2 drive pulse ----
      const pulse = (t * 1.2) % 1;
      const px = srcX - 74 + pulse * 74;
      ctx.strokeStyle = `rgba(192, 57, 43, ${0.85 * (1 - pulse * 0.4)})`;
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(px - 16, beamY);
      ctx.lineTo(px, beamY);
      ctx.stroke();

      // ---- plasma ----
      const hot = pulse > 0.9 || pulse < 0.2;
      const glowR = hot ? 17 + Math.sin(t * 44) * 3 : 10;
      const halo = ctx.createRadialGradient(srcX, beamY, 0, srcX, beamY, glowR * 2.6);
      halo.addColorStop(0, "rgba(255, 246, 220, 0.95)");
      halo.addColorStop(0.35, "rgba(255, 196, 120, 0.5)");
      halo.addColorStop(1, "rgba(255, 196, 120, 0)");
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(srcX, beamY, glowR * 2.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#5a53a3";
      ctx.beginPath();
      ctx.arc(srcX, beamY, 4, 0, Math.PI * 2);
      ctx.fill();

      // 4π emission — the light that never reaches the collector.
      for (let i = 0; i < 16; i++) {
        const a = (i / 16) * Math.PI * 2 + t * 0.5;
        const rr = 13 + ((t * 30 + i * 8) % 24);
        ctx.strokeStyle = `rgba(124, 92, 255, ${0.3 * (1 - rr / 38)})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(srcX + Math.cos(a) * rr, beamY + Math.sin(a) * rr);
        ctx.lineTo(srcX + Math.cos(a) * (rr + 6), beamY + Math.sin(a) * (rr + 6));
        ctx.stroke();
      }

      // ---- collector: the slice actually gathered ----
      ctx.strokeStyle = "rgba(181, 122, 46, 0.9)";
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.arc(srcX, beamY, 27, Math.PI - 0.6, Math.PI + 0.6);
      ctx.stroke();

      // ---- intermediate focus ----
      ctx.fillStyle = "rgba(90, 83, 163, 0.9)";
      ctx.beginPath();
      ctx.arc(ifX, beamY, 3.5, 0, Math.PI * 2);
      ctx.fill();

      // ---- optics ----
      nodes.forEach((n, i) => {
        ctx.save();
        ctx.translate(n.x, n.y);
        if (n.kind === "mask") {
          ctx.fillStyle = "#4b1d7e";
          ctx.strokeStyle = "#33145a";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.roundRect(-16, -4, 32, 8, 2);
          ctx.fill();
          ctx.stroke();
          // absorber pattern on the reticle
          ctx.fillStyle = "rgba(241,233,225,0.5)";
          for (let k = -12; k <= 12; k += 5) ctx.fillRect(k, -2, 2, 4);
        } else {
          ctx.rotate(n.y === topY ? 0.5 : -0.5);
          ctx.fillStyle = "#ddd8e4";
          ctx.strokeStyle = "#a9b1c7";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.roundRect(-11, -3, 22, 6, 2);
          ctx.fill();
          ctx.stroke();
        }
        ctx.restore();
      });

      // ---- wafer ----
      ctx.fillStyle = "#efe8e0";
      ctx.strokeStyle = "#c9bfa8";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(waferX, beamY, 21, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      const scan = ((t * 0.45) % 1) * 30 - 15;
      ctx.fillStyle = "rgba(124, 92, 255, 0.28)";
      ctx.fillRect(waferX - 9, beamY + scan - 2, 18, 4);

      // ---- emission + capture ----
      // 420 candidate photons/sec leave the plasma. Only `capture` of them are
      // inside the collector's solid angle. Rate is a simulation-speed knob;
      // the probability is not.
      if (!reduce) {
        spawnDebt += 420 * dt;
        while (spawnDebt >= 1 && photons.length < 140) {
          spawnDebt -= 1;
          tally.emitted++;
          if (Math.random() < capture) {
            tally.captured++;
            photons.push({ x: ifX, y: beamY, seg: 0, u: 0, alive: true });
          }
        }
      }

      // ---- transport ----
      const speed = 1.9; // segments per second
      for (const p of photons) {
        if (!p.alive) continue;
        p.u += speed * dt;
        while (p.u >= 1 && p.alive) {
          p.u -= 1;
          p.seg++;
          const node = nodes[p.seg - 1];
          if (node) {
            const survives =
              node.kind === "mask" ? Math.random() < maskGate : Math.random() < refl;
            if (!survives) {
              p.alive = false;
              flashes.push({ x: node.x, y: node.y, t0: now });
            }
          }
        }
        if (!p.alive) continue;
        const from = p.seg === 0 ? { x: ifX, y: beamY } : nodes[p.seg - 1];
        const to =
          p.seg >= nodes.length ? { x: waferX - 21, y: beamY } : nodes[p.seg];
        p.x = from.x + (to.x - from.x) * p.u;
        p.y = from.y + (to.y - from.y) * p.u;
        if (p.seg >= nodes.length && p.u > 0.97) {
          p.alive = false;
          tally.printed++;
        }
      }
      for (let i = photons.length - 1; i >= 0; i--) {
        if (!photons[i].alive) photons.splice(i, 1);
      }

      // ---- photons ----
      for (const p of photons) {
        ctx.strokeStyle = "rgba(124, 92, 255, 0.3)";
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(p.x - 7, p.y);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        ctx.fillStyle = "rgba(108, 76, 245, 0.95)";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2.3, 0, Math.PI * 2);
        ctx.fill();
      }

      // ---- absorption events ----
      for (let i = flashes.length - 1; i >= 0; i--) {
        const f = flashes[i];
        const age = (now - f.t0) / 420;
        if (age > 1) {
          flashes.splice(i, 1);
          continue;
        }
        ctx.strokeStyle = `rgba(192, 57, 43, ${0.75 * (1 - age)})`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(f.x, f.y, 4 + age * 10, 0, Math.PI * 2);
        ctx.stroke();
      }

      // ---- labels ----
      ctx.fillStyle = "#6f6a8a";
      ctx.font = "600 10px 'Cascadia Code', Consolas, monospace";
      ctx.textAlign = "center";
      ctx.fillText(`${(s.laser_power_kw ?? 0).toFixed(0)} kW CO2`, srcX, h * 0.9);
      ctx.fillText(`IF ${(s.intermediate_focus_power_w ?? 0).toFixed(0)} W`, ifX, h * 0.9);
      ctx.fillText(
        `${mirrors} mirrors · ${(s.mirror_reflectivity_pct ?? 0).toFixed(1)}% each`,
        (trainX0 + trainX1) / 2,
        h * 0.9
      );
      ctx.fillText(`${(s.wafer_plane_power_w ?? 0).toFixed(2)} W`, waferX, h * 0.9);
      ctx.fillStyle = "#4b1d7e";
      ctx.fillText("reticle", nodes[maskAt].x, nodes[maskAt].y - 9);
      ctx.textAlign = "left";

      // ---- sampled vs computed ----
      const sampled = tally.captured ? (tally.printed / tally.captured) * 100 : 0;
      ctx.fillStyle = "#453f63";
      ctx.font = "600 11px 'Cascadia Code', Consolas, monospace";
      ctx.fillText(
        `train transmission — computed ${trainTotal * 100 < 0.01 ? "<0.01" : (trainTotal * 100).toFixed(2)}%` +
          `   sampled ${sampled.toFixed(2)}%   (n=${tally.captured})`,
        14,
        16
      );
    };

    paint = render;

    // One synchronous frame: rAF does not run in a background or
    // non-compositing tab, and a blank panel reads as broken.
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
    };
  }, []);

  return (
    <div className="simflow">
      <canvas ref={ref} aria-hidden="true" />
      <div className="simflow-legend">
        <span><i className="sf-drive" />CO2 drive pulse</span>
        <span><i className="sf-euv" />13.5 nm photon</span>
        <span><i className="sf-mask" />reticle</span>
        <span><i className="sf-die" />absorbed</span>
      </div>
    </div>
  );
}

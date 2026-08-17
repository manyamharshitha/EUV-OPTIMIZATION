// Thin wrapper over the Python backend. Every screen's data comes from
// /api/run; the rest are on-demand endpoints for the interactive panels.

const qs = (params) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");

async function get(path, params = {}) {
  const query = qs(params);
  const response = await fetch(`${path}${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(`${path} -> ${response.status}`);
  }
  return response.json();
}

export const api = {
  run: (p) => get("/api/run", p),
  ai: (p) => get("/api/ai", p),
  goals: () => get("/api/goals"),
  design: (p) => get("/api/design", p),
  compareGoals: () => get("/api/compare-goals"),
  solve: (p) => get("/api/solve", p),
  costReduction: (p) => get("/api/cost-reduction", p),
  frontier: (p) => get("/api/frontier", p),
  alternatives: (p) => get("/api/alternatives", p),
  health: () => get("/api/health"),
};

export const money = (n) =>
  n === null || n === undefined || Number.isNaN(n)
    ? "—"
    : `$${Math.round(n).toLocaleString("en-US")}`;

export const compactMoney = (n) => {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${Math.round(n)}`;
};

/**
 * Integer counts, guarded. `n.toLocaleString()` on a null or a string throws,
 * and a throw inside render unmounts the whole tree — which is exactly how a
 * malformed payload was shown to blank all nine screens at once.
 */
export const count = (n, fallback = "—") =>
  typeof n === "number" && Number.isFinite(n)
    ? n.toLocaleString("en-US")
    : fallback;

export const num = (n, digits = 2) =>
  n === null || n === undefined || Number.isNaN(n)
    ? "—"
    : Number(n).toLocaleString("en-US", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

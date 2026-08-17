"""
serve.py  --  Person D (Product & Presentation)

Local web server for the EUV Components Optimizer.

    python serve.py          ->  http://localhost:8000

Deliberately built on http.server from the standard library rather than
Streamlit or Flask. Two reasons, and the second is the important one:

    1. Zero installs. The demo runs on a judge's laptop with nothing but
       Python, which removes the most common way a live demo dies.

    2. It preserves the claim the whole pitch rests on. `demo_proof.py`
       blocks every socket and runs the entire pipeline to prove the project
       needs no network. A pip-installed web framework would put third-party
       code in that path and weaken a claim we can currently make absolutely.

Binds to 127.0.0.1 only. Nothing on the local network can reach it.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
# Serve the built React bundle. `npm run build` in web/ produces it. During
# development `npm run dev` serves from source on 5173 and proxies /api here,
# so there is only ever one implementation of the data.
WEB_DIR = os.path.join(HERE, "web", "dist")
sys.path.insert(0, HERE)

HOST = "127.0.0.1"
PORT = 8000

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".ico": "image/x-icon",
}


def _float(params: dict, key: str, default=None):
    raw = params.get(key, [None])[0]
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int(params: dict, key: str, default=None):
    value = _float(params, key, None)
    return int(value) if value is not None else default


def _bool(params: dict, key: str, default=False):
    raw = params.get(key, [None])[0]
    if raw is None:
        return default
    return str(raw).lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def api_run(params: dict) -> dict:
    """The main pipeline. Everything the nine screens need, in one call."""
    import backend

    return backend.run(
        budget_usd=_float(params, "budget", 180_000_000.0),
        min_efficiency=_float(params, "efficiency", 0.50),
        max_timeline_years=_float(params, "timeline", 8.0),
        weight_cost=_float(params, "w_cost", 0.45),
        weight_efficiency=_float(params, "w_eff", 0.40),
        weight_time=_float(params, "w_time", 0.15),
        iso_class=_int(params, "iso", 3),
        dose_mj_cm2=_float(params, "dose", 20.0),
    )


_ai_cache: dict = {}
_ai_lock = threading.Lock()


def api_ai(params: dict) -> dict:
    """
    AI analysis for the current configuration, cached.

    On CPU a full pass is four model calls and measured at ~6 minutes on this
    class of machine. That is fine as a one-off and impossible live, so the
    result is cached per configuration and warmed in the background at server
    start. By the time anyone opens screen 7 the answer is already sitting
    here; only a configuration nobody has visited pays the wait.

    `?refresh=1` forces regeneration.
    """
    import backend

    key = (
        _float(params, "budget", 180_000_000.0),
        _float(params, "efficiency", 0.50),
        _float(params, "timeline", 8.0),
        _int(params, "iso", 3),
    )

    if not _bool(params, "refresh") and key in _ai_cache:
        cached = dict(_ai_cache[key])
        cached["cached"] = True
        return cached

    # One generation at a time. Two browser tabs asking at once would
    # otherwise queue two six-minute jobs against one CPU.
    with _ai_lock:
        if not _bool(params, "refresh") and key in _ai_cache:
            cached = dict(_ai_cache[key])
            cached["cached"] = True
            return cached

        result = backend.run(include_ai=True, budget_usd=key[0],
                             min_efficiency=key[1], max_timeline_years=key[2],
                             iso_class=key[3])["ai"]
        _ai_cache[key] = result

    fresh = dict(result)
    fresh["cached"] = False
    return fresh


def api_goals(params: dict) -> dict:
    import design_optimizer
    return {"goals": design_optimizer.GOALS}


def api_design(params: dict) -> dict:
    """Goal-driven optimisation -- 'tell it what you want'."""
    import design_optimizer
    import optimizer

    components = optimizer.load_components(_components_path())
    budget = _float(params, "budget")

    return design_optimizer.optimize_for(
        components,
        goal=params.get("goal", ["balanced"])[0],
        budget_usd=budget * 1e6 if budget else None,
        min_efficiency=_float(params, "efficiency"),
        min_throughput_wph=_float(params, "throughput"),
        exclude_hypothetical=_bool(params, "real_only"),
        top_n=5,
    )


def api_compare_goals(params: dict) -> dict:
    import design_optimizer
    import optimizer
    return design_optimizer.compare_goals(
        optimizer.load_components(_components_path()))


def api_solve(params: dict) -> dict:
    """Inverse solve -- pin what you know, solve for the rest."""
    import backend
    cost = _float(params, "max_cost")

    outcome = backend.solve_for(
        params.get("unknown", ["efficiency"])[0],
        max_cost=cost * 1e6 if cost else None,
        min_efficiency=_float(params, "min_efficiency"),
        max_timeline=_float(params, "max_timeline"),
    )
    return outcome


def api_cost_reduction(params: dict) -> dict:
    import backend
    target = _float(params, "target", 130.0)
    return backend.cost_reduction(
        target_cost_usd=target * 1e6,
        exclude_hypothetical=_bool(params, "real_only"))


def api_frontier(params: dict) -> dict:
    import backend
    return backend.tradeoff_frontier(max_points=_int(params, "points", 40))


def api_alternatives(params: dict) -> dict:
    import backend
    category = params.get("category", [None])[0]
    if not category:
        return {"ok": False, "reason": "category required"}
    return backend.alternatives_for(category)


def api_health(params: dict) -> dict:
    """Backend badge for the header -- is a local model actually live?"""
    sys.path.insert(0, os.path.join(HERE, "ai"))
    try:
        import ai_local_claude
        health = ai_local_claude.model_available()
        return {
            "local_model": health["available"] and health["target_model_present"],
            "reachable": health["available"],
            "model": ai_local_claude.MODEL_NAME,
            "endpoint": health["endpoint"],
        }
    except Exception as exc:
        return {"local_model": False, "reachable": False,
                "error": f"{type(exc).__name__}: {exc}"}


def _components_path() -> str:
    import backend
    return backend.DEFAULT_COMPONENTS_CSV


ROUTES = {
    "/api/run": api_run,
    "/api/ai": api_ai,
    "/api/goals": api_goals,
    "/api/design": api_design,
    "/api/compare-goals": api_compare_goals,
    "/api/solve": api_solve,
    "/api/cost-reduction": api_cost_reduction,
    "/api/frontier": api_frontier,
    "/api/alternatives": api_alternatives,
    "/api/health": api_health,
}


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "EUVOptimizer/1.0"

    def log_message(self, fmt, *args):
        """Quieter than the default, but keep errors visible.

        This used to test `"api" in args[0]` and print args[0] directly, which
        assumed the first argument was always the request line. It is not:
        send_error() logs through log_error("code %d, message %s", code, msg),
        where args[0] is an HTTPStatus. `"api" in HTTPStatus.NOT_IMPLEMENTED`
        raises TypeError, which killed the handler thread — so any request with
        an unsupported method dropped the connection instead of getting a 501.
        Rendering the format string first makes the filter work on real text
        whatever the caller passes.
        """
        try:
            line = fmt % args
        except (TypeError, ValueError):
            line = " ".join(str(a) for a in args) if args else str(fmt)
        if "api" in line:
            return
        sys.stderr.write(f"  {line}\n")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # The data changes on every slider move; never let a stale answer show.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        # HEAD sends the same headers as GET, including the real
        # Content-Length, but no body.
        if not getattr(self, "_head_only", False):
            self.wfile.write(body)

    def _send_json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def do_HEAD(self) -> None:
        """HEAD is GET with the body suppressed.

        Only do_GET was defined, so BaseHTTPRequestHandler answered HEAD with
        501 — visible in the log as `Unsupported method ('HEAD')`. RFC 9110
        requires GET and HEAD, and the preview tooling and ordinary health
        checks both probe with it.
        """
        self._head_only = True
        try:
            self.do_GET()
        finally:
            self._head_only = False

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        handler = ROUTES.get(path)
        if handler:
            try:
                self._send_json(handler(params))
            except Exception as exc:
                traceback.print_exc()
                self._send_json(
                    {"ok": False,
                     "error": f"{type(exc).__name__}: {exc}"}, 500)
            return

        # Static files
        if path == "/":
            path = "/index.html"

        target = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
        if not target.startswith(WEB_DIR) or not os.path.isfile(target):
            self._send(404, b"not found", "text/plain")
            return

        extension = os.path.splitext(target)[1]
        with open(target, "rb") as handle:
            self._send(200, handle.read(),
                       MIME.get(extension, "application/octet-stream"))


def main() -> int:
    if not os.path.isdir(WEB_DIR):
        print(f"  No built UI at {WEB_DIR}\n")
        print("  Build it once:")
        print("    cd web && npm install && npm run build\n")
        print("  The API is still up, so `npm run dev` in web/ works now.\n")

    def warm():
        """
        Warm the pipeline, then the AI cache for the default configuration.

        The optimiser warms in under a second. The AI pass takes minutes on
        CPU, which is exactly why it happens here at startup instead of when
        a judge clicks screen 7.
        """
        try:
            import backend
            backend.run()
            print("  optimiser ready")
        except Exception:
            return

        try:
            import ai_local_claude
            health = ai_local_claude.model_available(force=True)
            if not (health["available"] and health["target_model_present"]):
                print("  no local model — AI panels will be rule-based")
                return

            print("  warming AI cache in background (several minutes on CPU)…")
            api_ai({})
            print("  AI cache ready")
        except Exception as exc:
            print(f"  AI warm-up skipped: {type(exc).__name__}")

    threading.Thread(target=warm, daemon=True).start()

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 62)
    print("  EUV COMPONENTS OPTIMIZER")
    print("=" * 62)
    print(f"\n  http://{HOST}:{PORT}\n")
    print("  Bound to loopback only. Nothing on your network can reach it.")
    print("  Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

import { Component } from "react";

/**
 * Error boundary around the screen area.
 *
 * Without one, a single bad field anywhere in nine screens unmounts the whole
 * React tree and the app goes black — masthead, navigation and all — with no
 * way back except a reload. That was demonstrated: feeding /api/run a payload
 * with the right keys and wrong types blanked every screen and the home
 * launcher together.
 *
 * The backend is ours and returns well-formed data, so this should never fire.
 * It exists because the cost of being wrong about that is the entire demo
 * going dark in front of a judge, and the cost of the guard is this file.
 *
 * It wraps only the screen body. The masthead, badges and footer stay mounted,
 * so a failure on one screen leaves the other eight reachable.
 *
 * React has no hook equivalent — getDerivedStateFromError is class-only.
 */
export class Boundary extends Component {
  constructor(props) {
    super(props);
    this.state = { err: null };
  }

  static getDerivedStateFromError(err) {
    return { err };
  }

  componentDidCatch(err, info) {
    // Kept visible rather than swallowed: a screen that silently degrades is
    // worse than one that says what broke.
    console.error("screen crashed:", err, info?.componentStack);
  }

  componentDidUpdate(prev) {
    // Navigating away from a broken screen clears it, so one bad screen does
    // not poison the rest of the session.
    if (prev.resetKey !== this.props.resetKey && this.state.err) {
      this.setState({ err: null });
    }
  }

  render() {
    if (!this.state.err) return this.props.children;
    return (
      <main className="view">
        <div className="grid">
          <section className="panel">
            <h2>
              <span className="idx">!!</span> This screen failed to render
            </h2>
            <p className="note">
              {String(this.state.err?.message || this.state.err)}
            </p>
            <p className="note">
              The other screens are unaffected — press Esc for home, or 1–9 to
              jump. Nothing was lost; the run is still in memory.
            </p>
          </section>
        </div>
      </main>
    );
  }
}

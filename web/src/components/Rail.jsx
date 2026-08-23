// Left-corner rail: every screen, one click away, from anywhere in the app.
//
// Without this, reaching screen 7 from screen 2 meant either five Next clicks
// or a trip back through Home's tiles. Fixed to the viewport rather than the
// shell, so it stays put while the page under it scrolls or changes.
import { SCREENS } from "../screens.jsx";

export function Rail({ current, onSelect }) {
  return (
    <nav className="rail" aria-label="Jump to screen">
      <button
        className={`rail-item rail-home ${current === 0 ? "on" : ""}`}
        onClick={() => onSelect(0)}
        title="Home"
        aria-label="Home"
        aria-current={current === 0 ? "page" : undefined}
      >
        <span className="rail-dot" aria-hidden="true" />
      </button>
      <div className="rail-sep" aria-hidden="true" />
      {SCREENS.map((s) => (
        <button
          key={s.id}
          className={`rail-item ${current === s.id ? "on" : ""}`}
          onClick={() => onSelect(s.id)}
          title={s.name}
          aria-label={`${s.id}. ${s.name}`}
          aria-current={current === s.id ? "page" : undefined}
          style={{ "--accent": s.colour, "--accent-ink": s.ink }}
        >
          {s.id}
        </button>
      ))}
    </nav>
  );
}

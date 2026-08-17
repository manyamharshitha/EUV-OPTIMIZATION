// Small shared primitives. Kept deliberately plain — the visual character
// lives in styles.css so a designer can retune it without touching React.

export function Panel({ idx, title, wide, children }) {
  return (
    <section className={`panel ${wide ? "span-2" : ""}`}>
      <h2>
        <span className="idx">{idx}</span>
        {title}
      </h2>
      {children}
    </section>
  );
}

export function Readout({ tone = "", children }) {
  return <div className={`readout ${tone}`}>{children}</div>;
}

export function Bar({ pct, tone = "" }) {
  const width = Math.max(0, Math.min(100, Number(pct) || 0));
  return (
    <div className={`bar ${tone}`}>
      <i style={{ width: `${width}%` }} />
    </div>
  );
}

export function Slider({ label, value, min, max, step, onChange, display }) {
  // Fill the track up to the thumb so the control reads as a gauge.
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="control">
      <label>
        <span>{label}</span>
        <b>{display}</b>
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        style={{ "--pct": `${pct}%` }}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

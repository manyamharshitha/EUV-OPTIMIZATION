// The disclosure band.
//
// BACKEND_CONTRACT.md requires every `critical` and `high` entry to render
// beside the numbers it qualifies, before a judge reads them -- not in a
// footer, tooltip, or about page. This sits directly under the header and
// above every result panel, and it re-renders on every run because severity
// changes with the configuration: the default is all-real parts, a
// cost-focused one can be 88% hardware that does not exist.

export function Disclosures({ disclosure }) {
  const shown = (disclosure.entries || []).filter((e) =>
    ["critical", "high"].includes(e.severity)
  );

  if (shown.length === 0) return null;

  return (
    <div className="disclosures">
      {shown.map((entry) => (
        <div className={`disclose ${entry.severity}`} key={entry.id}>
          <span className="sev">{entry.severity}</span>
          <div className="body">
            <div className="head">{entry.headline}</div>
            <div className="say">{entry.say_this}</div>
            {entry.parts?.length > 0 && (
              <div style={{ marginTop: 9, display: "flex", flexWrap: "wrap", gap: 6 }}>
                {entry.parts.map((p, i) => (
                  <span className="chip hyp" key={i}>
                    {p.category} · {p.country}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

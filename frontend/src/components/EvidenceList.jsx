export default function EvidenceList({ title, items }) {
  if (!items || items.length === 0) {
    return (
      <div className="evidence-block">
        <div className="evidence-block-title">{title}</div>
        <p style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
          No evidence found.
        </p>
      </div>
    );
  }

  return (
    <div className="evidence-block">
      <div className="evidence-block-title">{title}</div>
      {items.map((item, idx) => (
        <div key={idx} className="evidence-item">
          <div className="evidence-meta">
            {item.chapter && `${item.chapter} · `}
            {item.section && `Section ${item.section} · `}
            {item.page != null && `Page ${item.page} · `}
            match score: {(1 / (1 + item.distance)).toFixed(2)}
          </div>
          <div className="evidence-text">{item.text}</div>
        </div>
      ))}
    </div>
  );
}
import { useState } from "react";

const OPTIONS = [
  { value: "ACCEPT", label: "✓ Accept Paper" },
  { value: "REJECT", label: "✗ Reject Paper" },
  { value: "OVERRIDE", label: "⟳ Override Paper" },
];

export default function PaperDecisionForm({ totalQuestions, saving, onApply }) {
  const [choice, setChoice] = useState(null);
  const [comment, setComment] = useState("");

  const handleApply = async () => {
    if (!choice) return;
    const ok = window.confirm(
      `Apply "${choice}" to all ${totalQuestions} questions?\n\n` +
      `This overwrites any decisions already recorded on individual questions.`
    );
    if (!ok) return;
    const success = await onApply(choice, comment);
    if (success) {
      setChoice(null);
      setComment("");
    }
  };

  const handleReset = async () => {
    const ok = window.confirm(`Reset all ${totalQuestions} questions back to PENDING?`);
    if (!ok) return;
    await onApply("PENDING", "");
  };

  return (
    <div>
      <div className="decision-scroll">
        {OPTIONS.map((o) => (
          <button
            key={o.value}
            type="button"
            className={`decision-pill ${choice === o.value ? `active-${o.value}` : ""}`}
            onClick={() => setChoice(o.value)}
          >
            {o.label}
          </button>
        ))}
      </div>

      <div className="form-group" style={{ marginTop: 12 }}>
        <label className="form-label">Comment (optional)</label>
        <textarea
          className="form-input"
          rows={2}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Saved against every question's record..."
        />
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button type="button" className="btn btn-primary" onClick={handleApply} disabled={!choice || saving}>
          {saving ? "Applying..." : choice ? `Apply "${choice}" to all questions` : "Select a decision"}
        </button>
        <button type="button" className="btn btn-secondary" onClick={handleReset} disabled={saving}>
          Reset all to Pending
        </button>
      </div>
    </div>
  );
}
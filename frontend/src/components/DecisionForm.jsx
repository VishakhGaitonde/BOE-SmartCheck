import { useState } from "react";

const DECISIONS = [
  { value: "ACCEPT", label: "✓ Accept" },
  { value: "REJECT", label: "✗ Reject" },
  { value: "OVERRIDE", label: "⟳ Override" },
  { value: "PENDING", label: "⏸ Pending" },
];

export default function DecisionForm({ existingDecision, onSave, saving }) {
  const [decision, setDecision] = useState(existingDecision?.decision || "PENDING");
  const [comment, setComment] = useState(existingDecision?.comment || "");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(decision, comment);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="decision-scroll">
        {DECISIONS.map((d) => (
          <button
            key={d.value}
            type="button"
            className={`decision-pill ${decision === d.value ? `active-${d.value}` : ""}`}
            onClick={() => setDecision(d.value)}
          >
            {d.label}
          </button>
        ))}
      </div>

      <div className="form-group" style={{ marginTop: 12 }}>
        <label className="form-label">Comment (optional)</label>
        <textarea
          className="form-input"
          rows={3}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Reason for decision, notes for the record..."
        />
      </div>

      <button type="submit" className="btn btn-primary" disabled={saving}>
        {saving ? "Saving..." : "Save Decision"}
      </button>

      {existingDecision && (
        <p className="form-hint" style={{ marginTop: 10 }}>
          Last decided by {existingDecision.decided_by} on{" "}
          {new Date(existingDecision.decided_at).toLocaleString()}
        </p>
      )}
    </form>
  );
}
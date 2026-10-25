import { useState } from "react";

const DECISIONS = [
  { value: "ACCEPT", label: "Accept" },
  { value: "REJECT", label: "Reject" },
  { value: "OVERRIDE", label: "Override" },
  { value: "PENDING", label: "Pending" },
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
      <div className="form-group">
        <label className="form-label">BOE Decision</label>
        <select className="form-select" value={decision} onChange={(e) => setDecision(e.target.value)}>
          {DECISIONS.map((d) => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
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
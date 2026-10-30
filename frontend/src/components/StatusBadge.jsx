const VARIANTS = {
  SUPPORTED: "badge-success",
  PASSED: "badge-success",
  ACCEPTED: "badge-success",
  ACCEPT: "badge-success",
  ALIGNED: "badge-success",
  VERIFIED_BY_BOE: "badge-success",
  REQUIRES_REVIEW: "badge-warning",
  REQUIRES_BOE_REVIEW: "badge-warning",
  OVERRIDE: "badge-warning",
  POTENTIAL_MISMATCH: "badge-warning",
  UNCERTAIN: "badge-pending",
  POTENTIALLY_UNRELATED: "badge-danger",
  REJECT: "badge-danger",
  REJECTED: "badge-danger",
  PENDING: "badge-pending",
  OVERRIDDEN: "badge-warning",
};

export default function StatusBadge({ status, label }) {
  const variant = VARIANTS[status] || "badge-pending";
  return <span className={`badge ${variant}`}>{label || status || "PENDING"}</span>;
}
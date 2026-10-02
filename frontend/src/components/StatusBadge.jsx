const VARIANTS = {
  SUPPORTED: "badge-success",
  PASSED: "badge-success",
  ACCEPTED: "badge-success",
  ACCEPT: "badge-success",
  REQUIRES_REVIEW: "badge-warning",
  REQUIRES_BOE_REVIEW: "badge-warning",
  OVERRIDE: "badge-warning",
  POTENTIALLY_UNRELATED: "badge-danger",
  REJECT: "badge-danger",
  REJECTED: "badge-danger",
  PENDING: "badge-pending",
};

export default function StatusBadge({ status }) {
  const variant = VARIANTS[status] || "badge-pending";
  return <span className={`badge ${variant}`}>{status || "PENDING"}</span>;
}
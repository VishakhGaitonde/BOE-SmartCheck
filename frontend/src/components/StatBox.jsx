export default function StatBox({ value, label }) {
  return (
    <div className="stat-box">
      <div className="stat-box-value">{value}</div>
      <div className="stat-box-label">{label}</div>
    </div>
  );
}
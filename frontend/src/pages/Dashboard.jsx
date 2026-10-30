import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPapers, deletePaper } from "../api/papers";
import Navbar from "../components/Navbar";
import StatusBadge from "../components/StatusBadge";

export default function Dashboard() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    listPapers()
      .then((res) => setPapers(res.data))
      .catch(() => setError("Failed to load papers."))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (paper) => {
    const confirmed = window.confirm(
      `Permanently delete "${paper.paper_name}"?\n\n` +
      `This removes the paper, its uploaded files, all AI results and BOE decisions. ` +
      `This cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingId(paper.id);
    setError("");
    try {
      await deletePaper(paper.id);
      setPapers((prev) => prev.filter((p) => p.id !== paper.id));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to delete paper.");
    } finally {
      setDeletingId(null);
    }
  };

  const isVerifiedByBoe = (p) => p.final_boe_status && p.final_boe_status !== "PENDING";

  return (
    <div>
      <Navbar />
      <div className="page">
        <div className="page-header">
          <h2>Dashboard</h2>
          <Link to="/new-verification">
            <button className="btn btn-primary">+ New SEE Verification</button>
          </Link>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading && <p>Loading papers...</p>}

        {!loading && papers.length === 0 && (
          <div className="card empty-state">
            <p>No papers verified yet.</p>
            <Link to="/new-verification">
              <button className="btn btn-primary" style={{ marginTop: 8 }}>
                Start your first verification
              </button>
            </Link>
          </div>
        )}

        {!loading && papers.length > 0 && (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Paper</th>
                  <th>Course</th>
                  <th>Pattern</th>
                  <th>Date</th>
                  <th>AI Status</th>
                  <th>BOE Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {papers.map((p) => (
                  <tr key={p.id}>
                    <td>{p.paper_name}</td>
                    <td>{p.course || "-"}</td>
                    <td>{p.pattern} marks</td>
                    <td>{new Date(p.uploaded_at).toLocaleDateString()}</td>
                    <td>
                      {isVerifiedByBoe(p)
                        ? <StatusBadge status="VERIFIED_BY_BOE" label="VERIFIED BY BOE" />
                        : <StatusBadge status={p.overall_ai_status} />}
                    </td>
                    <td><StatusBadge status={p.final_boe_status} /></td>
                    <td>
                      <Link to={`/papers/${p.id}`}>View →</Link>
                      <button
                        className="btn btn-danger btn-sm"
                        style={{ marginLeft: 12 }}
                        onClick={() => handleDelete(p)}
                        disabled={deletingId === p.id}
                      >
                        {deletingId === p.id ? "Deleting..." : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
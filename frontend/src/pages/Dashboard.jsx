import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPapers } from "../api/papers";
import Navbar from "../components/Navbar";
import StatusBadge from "../components/StatusBadge";

export default function Dashboard() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listPapers()
      .then((res) => setPapers(res.data))
      .catch(() => setError("Failed to load papers."))
      .finally(() => setLoading(false));
  }, []);

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
                    <td><StatusBadge status={p.overall_ai_status} /></td>
                    <td><StatusBadge status={p.final_boe_status} /></td>
                    <td><Link to={`/papers/${p.id}`}>View →</Link></td>
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
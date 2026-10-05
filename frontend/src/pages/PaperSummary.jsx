import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPaper, listDocuments, listQuestions, getValidation, validateMarks } from "../api/papers";
import Navbar from "../components/Navbar";
import StatusBadge from "../components/StatusBadge";
import StatBox from "../components/StatBox";

export default function PaperSummary() {
  const { paperId } = useParams();
  const [paper, setPaper] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [validation, setValidation] = useState(null);
  const [validationError, setValidationError] = useState("");

  useEffect(() => {
    getPaper(paperId).then((res) => setPaper(res.data));
    listDocuments(paperId).then((res) => setDocuments(res.data));
    listQuestions(paperId).then((res) => setQuestions(res.data));
    loadValidation();
  }, [paperId]);

  const loadValidation = () => {
    getValidation(paperId)
      .then((res) => setValidation(res.data))
      .catch(() => setValidation(null));
  };

  const runValidation = async () => {
    try {
      const res = await validateMarks(paperId);
      setValidation(res.data);
      setValidationError("");
    } catch (err) {
      setValidationError(err.response?.data?.detail || "Validation failed.");
    }
  };

  if (!paper) {
    return (
      <div>
        <Navbar />
        <div className="page">Loading...</div>
      </div>
    );
  }

  return (
    <div>
      <Navbar />
      <div className="page">
        <Link to="/dashboard" className="back-link">← Back to Dashboard</Link>

        <div className="card">
          <div className="page-header">
            <div>
              <h2 className="card-title">{paper.paper_name}</h2>
              <p className="card-subtitle">{paper.course || "No course specified"}</p>
            </div>
            <StatusBadge status={paper.final_boe_status} />
          </div>

          <div className="stat-grid">
            <StatBox value={`${paper.pattern}`} label="Max Marks" />
            <StatBox value={questions.length} label="Questions" />
            <StatBox value={paper.calculated_marks ?? "-"} label="Calculated Marks" />
            <StatBox value={paper.structure_type === "UNIT_OR" ? "Unit/OR" : "Section A-E"} label="Pattern Type" />
          </div>

          <Link to={`/papers/${paperId}/questions`}>
            <button className="btn btn-primary">View Question-wise Verification →</button>
          </Link>
        </div>

        {/* ---------- Marks Validation ---------- */}
        <div className="page-header" style={{ marginTop: 28 }}>
          <h3 className="section-heading" style={{ margin: 0 }}>Marks Validation</h3>
          <button className="btn btn-secondary btn-sm" onClick={runValidation}>
            {validation ? "Re-run Validation" : "Run Validation"}
          </button>
        </div>

        {validationError && <div className="alert alert-error">{validationError}</div>}

        {validation && (
          <div className="card">
            <div style={{ display: "flex", gap: 24, marginBottom: 12 }}>
              <div><strong>Expected:</strong> {validation.expected_total_marks}</div>
              <div><strong>Calculated:</strong> {validation.calculated_total_marks}</div>
              <StatusBadge status={validation.overall_valid ? "SUPPORTED" : "REQUIRES_BOE_REVIEW"} />
            </div>

            {validation.unit_results.length > 0 && (
              <div className="table-wrap">
                {validation.unit_results.map((u, idx) => (
                  <div className="unit-row" key={idx}>
                    <span className="unit-row-label">{u.unit} — Q{u.question_number}</span>
                    <span className="unit-row-marks">
                      {u.actual_marks}/{u.expected_marks} {u.valid ? "✓" : "✗"}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {validation.sections.length > 0 && (
              <div className="table-wrap">
                {validation.sections.map((s, idx) => (
                  <div className="unit-row" key={idx}>
                    <span className="unit-row-label">Section {s.section}</span>
                    <span className="unit-row-marks">
                      {s.actual_marks}/{s.expected_marks} {s.valid ? "✓" : "✗"}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {validation.issues.length > 0 && (
              <div style={{ marginTop: 12 }}>
                {validation.issues.map((issue, idx) => (
                  <div key={idx} className="alert alert-error" style={{ marginBottom: 6 }}>
                    {issue}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ---------- Documents ---------- */}
        <h3 className="section-heading">Documents</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Filename</th>
                <th>OCR Used</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((d) => (
                <tr key={d.id}>
                  <td style={{ textTransform: "capitalize" }}>{d.document_type.replace("_", " ")}</td>
                  <td>{d.filename}</td>
                  <td>{d.was_ocr === "yes" ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
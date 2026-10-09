import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getPaper,
  listDocuments,
  listQuestions,
  getValidation,
  validateMarks,
  verifyQuestions,
  listVerifications,
} from "../api/papers";
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

  const [verifications, setVerifications] = useState([]);
  const [verifyStatus, setVerifyStatus] = useState("");
  const [verifyError, setVerifyError] = useState("");
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    getPaper(paperId).then((res) => setPaper(res.data));
    listDocuments(paperId).then((res) => setDocuments(res.data));
    listQuestions(paperId).then((res) => setQuestions(res.data));
    loadValidation();
    loadVerifications();
  }, [paperId]);

  const loadValidation = () => {
    getValidation(paperId)
      .then((res) => setValidation(res.data))
      .catch(() => setValidation(null));
  };

  const loadVerifications = () => {
    listVerifications(paperId).then((res) => setVerifications(res.data));
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

  const runVerification = async () => {
    setVerifying(true);
    setVerifyError("");
    setVerifyStatus("");
    try {
      const res = await verifyQuestions(paperId, false);
      setVerifyStatus(res.data.message);
      loadVerifications();
    } catch (err) {
      setVerifyError(err.response?.data?.detail || "Verification failed.");
    } finally {
      setVerifying(false);
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

        {/* ---------- AI Verification ---------- */}
        <h3 className="section-heading">AI Verification</h3>
        <div className="card">
          <div className="stat-grid">
            <StatBox value={questions.length} label="Total Questions" />
            <StatBox
              value={verifications.filter((v) => v.ai_status === "SUPPORTED").length}
              label="Supported"
            />
            <StatBox
              value={verifications.filter((v) => v.ai_status === "REQUIRES_REVIEW").length}
              label="Requires Review"
            />
            <StatBox
              value={verifications.filter((v) => v.ai_status === "POTENTIALLY_UNRELATED").length}
              label="Unrelated"
            />
          </div>

          {verifications.length < questions.length && (
            <div className="alert alert-error" style={{ marginBottom: 12 }}>
              {verifications.length} of {questions.length} questions verified so far
              {verifications.length > 0 ? " — likely stopped due to LLM quota." : "."}
            </div>
          )}

          <button className="btn btn-secondary btn-sm" onClick={runVerification} disabled={verifying}>
            {verifying ? "Verifying..." : "Resume / Continue Verification"}
          </button>

          {verifyStatus && <div className="alert alert-success" style={{ marginTop: 12 }}>{verifyStatus}</div>}
          {verifyError && <div className="alert alert-error" style={{ marginTop: 12 }}>{verifyError}</div>}
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
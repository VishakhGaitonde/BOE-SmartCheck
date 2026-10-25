import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getPaper,
  listDocuments,
  listQuestions,
  getValidation,
  validateMarks,
  verifyAndAnalyze,
  listVerifications,
  analyzeCoBloom,
  listCoBloomResults,
  detectDuplicates,
  listDuplicates,
  aggregateSummary,
  getPaperCoordinatorSummary,
  downloadReport,
  getDecisionSummary,
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

  const [coBloomResults, setCoBloomResults] = useState([]);
  const [coBloomStatus, setCoBloomStatus] = useState("");
  const [coBloomError, setCoBloomError] = useState("");
  const [analyzingCoBloom, setAnalyzingCoBloom] = useState(false);

  const [duplicates, setDuplicates] = useState([]);
  const [dupStatus, setDupStatus] = useState("");
  const [dupError, setDupError] = useState("");
  const [detecting, setDetecting] = useState(false);

  const [coordSummary, setCoordSummary] = useState(null);
  const [coordError, setCoordError] = useState("");
  const [aggregating, setAggregating] = useState(false);

  const [decisionSummary, setDecisionSummary] = useState(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    getPaper(paperId).then((res) => setPaper(res.data));
    listDocuments(paperId).then((res) => setDocuments(res.data));
    listQuestions(paperId).then((res) => setQuestions(res.data));
    loadValidation();
    loadVerifications();
    loadCoBloom();
    loadDuplicates();
    loadCoordSummary();
    loadDecisionSummary();
  }, [paperId]);

  const loadValidation = () => getValidation(paperId).then((res) => setValidation(res.data)).catch(() => setValidation(null));
  const loadVerifications = () => listVerifications(paperId).then((res) => setVerifications(res.data));
  const loadCoBloom = () => listCoBloomResults(paperId).then((res) => setCoBloomResults(res.data));
  const loadDuplicates = () => listDuplicates(paperId).then((res) => setDuplicates(res.data));
  const loadCoordSummary = () => getPaperCoordinatorSummary(paperId).then((res) => setCoordSummary(res.data)).catch(() => setCoordSummary(null));
  const loadDecisionSummary = () => getDecisionSummary(paperId).then((res) => setDecisionSummary(res.data));

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
      const res = await verifyAndAnalyze(paperId, false);
      setVerifyStatus(res.data.message);
      loadVerifications();
      loadCoBloom();
    } catch (err) {
      setVerifyError(err.response?.data?.detail || "Verification failed.");
    } finally {
      setVerifying(false);
    }
  };

  const runCoBloomAnalysis = async () => {
    setAnalyzingCoBloom(true);
    setCoBloomError("");
    setCoBloomStatus("");
    try {
      const res = await analyzeCoBloom(paperId);
      setCoBloomStatus(res.data.message);
      loadCoBloom();
    } catch (err) {
      setCoBloomError(err.response?.data?.detail || "CO/Bloom analysis failed.");
    } finally {
      setAnalyzingCoBloom(false);
    }
  };

  const runDetectDuplicates = async () => {
    setDetecting(true);
    setDupError("");
    setDupStatus("");
    try {
      const res = await detectDuplicates(paperId);
      setDuplicates(res.data);
      setDupStatus(`Found ${res.data.length} flagged pair(s).`);
    } catch (err) {
      setDupError(err.response?.data?.detail || "Duplicate detection failed.");
    } finally {
      setDetecting(false);
    }
  };

  const runAggregateSummary = async () => {
    setAggregating(true);
    setCoordError("");
    try {
      const res = await aggregateSummary(paperId);
      setCoordSummary(res.data);
    } catch (err) {
      setCoordError(err.response?.data?.detail || "Aggregation failed.");
    } finally {
      setAggregating(false);
    }
  };

  const handleDownloadReport = async () => {
    setDownloading(true);
    try {
      await downloadReport(paperId, paper?.paper_name);
    } finally {
      setDownloading(false);
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

  const qnumById = {};
  questions.forEach((q) => { qnumById[q.id] = q.question_number; });

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

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Link to={`/papers/${paperId}/questions`}>
              <button className="btn btn-primary">View Question-wise Verification →</button>
            </Link>
            <button className="btn btn-secondary" onClick={handleDownloadReport} disabled={downloading}>
              {downloading ? "Generating..." : "Download PDF Report"}
            </button>
          </div>
        </div>

        {/* ---------- Overall AI Recommendation (Coordinator) ---------- */}
        <h3 className="section-heading">Overall AI Recommendation</h3>
        <div className="card">
          {coordSummary ? (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <StatusBadge status={coordSummary.overall_status} />
                <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                  {coordSummary.marks_valid ? "Marks valid" : "Marks invalid"}
                </span>
              </div>
              {coordSummary.reasons.length > 0 && (
                <div>
                  {coordSummary.reasons.map((r, idx) => (
                    <div key={idx} className="alert alert-error" style={{ marginBottom: 6 }}>{r}</div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Not yet generated. Run marks validation, AI verification, CO/Bloom analysis, and duplicate detection first, then generate the overall summary.
            </p>
          )}

          {coordError && <div className="alert alert-error" style={{ marginTop: 12 }}>{coordError}</div>}

          <button className="btn btn-secondary btn-sm" onClick={runAggregateSummary} disabled={aggregating} style={{ marginTop: 12 }}>
            {aggregating ? "Aggregating..." : coordSummary ? "Re-generate Overall Summary" : "Generate Overall Summary"}
          </button>
        </div>

        {/* ---------- AI Verification ---------- */}
        <h3 className="section-heading">AI Verification</h3>
        <div className="card">
          <div className="stat-grid">
            <StatBox value={questions.length} label="Total Questions" />
            <StatBox value={verifications.filter((v) => v.ai_status === "SUPPORTED").length} label="Supported" />
            <StatBox value={verifications.filter((v) => v.ai_status === "REQUIRES_REVIEW").length} label="Requires Review" />
            <StatBox value={verifications.filter((v) => v.ai_status === "POTENTIALLY_UNRELATED").length} label="Unrelated" />
          </div>

          {verifications.length < questions.length && (
            <div className="alert alert-error" style={{ marginBottom: 12 }}>
              {verifications.length} of {questions.length} questions verified so far.
            </div>
          )}

          <button className="btn btn-secondary btn-sm" onClick={runVerification} disabled={verifying}>
            {verifying ? "Verifying..." : "Resume / Continue Verification"}
          </button>

          {verifyStatus && <div className="alert alert-success" style={{ marginTop: 12 }}>{verifyStatus}</div>}
          {verifyError && <div className="alert alert-error" style={{ marginTop: 12 }}>{verifyError}</div>}
        </div>

        {/* ---------- CO & Bloom ---------- */}
        <h3 className="section-heading">CO & Bloom's Taxonomy Analysis</h3>
        <div className="card">
          <div className="stat-grid">
            <StatBox value={coBloomResults.length} label="Analyzed" />
            <StatBox value={coBloomResults.filter((c) => c.co_alignment === "ALIGNED").length} label="Aligned" />
            <StatBox value={coBloomResults.filter((c) => c.co_alignment === "POTENTIAL_MISMATCH").length} label="Potential Mismatch" />
            <StatBox value={coBloomResults.filter((c) => c.co_alignment === "UNCERTAIN").length} label="Uncertain" />
          </div>

          {coBloomResults.length < questions.length && (
            <div className="alert alert-error" style={{ marginBottom: 12 }}>
              {coBloomResults.length} of {questions.length} questions analyzed so far.
            </div>
          )}

          <button className="btn btn-secondary btn-sm" onClick={runCoBloomAnalysis} disabled={analyzingCoBloom}>
            {analyzingCoBloom ? "Analyzing..." : "Resume / Continue CO-Bloom Analysis"}
          </button>

          {coBloomStatus && <div className="alert alert-success" style={{ marginTop: 12 }}>{coBloomStatus}</div>}
          {coBloomError && <div className="alert alert-error" style={{ marginTop: 12 }}>{coBloomError}</div>}
        </div>

        {/* ---------- Duplication Detection ---------- */}
        <h3 className="section-heading">Duplication Detection</h3>
        <div className="card">
          <div className="stat-grid">
            <StatBox value={duplicates.filter((d) => d.status === "LIKELY_DUPLICATE").length} label="Likely Duplicates" />
            <StatBox value={duplicates.filter((d) => d.status === "POSSIBLE_DUPLICATE").length} label="Possible Duplicates" />
          </div>

          {duplicates.length > 0 && (
            <div className="table-wrap" style={{ marginBottom: 12 }}>
              {duplicates.map((d, idx) => (
                <div className="unit-row" key={idx}>
                  <span className="unit-row-label">
                    Q{qnumById[d.question_id_a] || d.question_id_a} ↔ Q{qnumById[d.question_id_b] || d.question_id_b}
                  </span>
                  <span className="unit-row-marks">
                    <StatusBadge status={d.status} /> {d.similarity.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}

          <button className="btn btn-secondary btn-sm" onClick={runDetectDuplicates} disabled={detecting}>
            {detecting ? "Detecting..." : duplicates.length > 0 ? "Re-run Duplicate Detection" : "Detect Duplicates"}
          </button>

          {dupStatus && <div className="alert alert-success" style={{ marginTop: 12 }}>{dupStatus}</div>}
          {dupError && <div className="alert alert-error" style={{ marginTop: 12 }}>{dupError}</div>}
        </div>

        {/* ---------- BOE Decisions ---------- */}
        <h3 className="section-heading">BOE Decisions</h3>
        <div className="card">
          {decisionSummary && (
            <div className="stat-grid">
              <StatBox value={decisionSummary.decided} label={`Decided / ${decisionSummary.total_questions}`} />
              <StatBox value={decisionSummary.accepted} label="Accepted" />
              <StatBox value={decisionSummary.rejected} label="Rejected" />
              <StatBox value={decisionSummary.overridden} label="Overridden" />
            </div>
          )}
          <Link to={`/papers/${paperId}/questions`}>
            <button className="btn btn-secondary btn-sm">Review & Decide →</button>
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
                    <span className="unit-row-marks">{u.actual_marks}/{u.expected_marks} {u.valid ? "✓" : "✗"}</span>
                  </div>
                ))}
              </div>
            )}

            {validation.sections.length > 0 && (
              <div className="table-wrap">
                {validation.sections.map((s, idx) => (
                  <div className="unit-row" key={idx}>
                    <span className="unit-row-label">Section {s.section}</span>
                    <span className="unit-row-marks">{s.actual_marks}/{s.expected_marks} {s.valid ? "✓" : "✗"}</span>
                  </div>
                ))}
              </div>
            )}

            {validation.issues.length > 0 && (
              <div style={{ marginTop: 12 }}>
                {validation.issues.map((issue, idx) => (
                  <div key={idx} className="alert alert-error" style={{ marginBottom: 6 }}>{issue}</div>
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
              <tr><th>Type</th><th>Filename</th><th>OCR Used</th></tr>
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
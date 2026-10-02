import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPaper, listDocuments, listQuestions } from "../api/papers";
import Navbar from "../components/Navbar";
import StatusBadge from "../components/StatusBadge";

export default function PaperSummary() {
  const { paperId } = useParams();
  const [paper, setPaper] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [questions, setQuestions] = useState([]);

  useEffect(() => {
    getPaper(paperId).then((res) => setPaper(res.data));
    listDocuments(paperId).then((res) => setDocuments(res.data));
    listQuestions(paperId).then((res) => setQuestions(res.data));
  }, [paperId]);

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

          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 8 }}>
            <div><strong>Pattern:</strong> {paper.pattern} marks</div>
            <div><strong>Questions:</strong> {questions.length}</div>
            <div><strong>Calculated Marks:</strong> {paper.calculated_marks ?? "-"}</div>
          </div>
        </div>

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

        <h3 className="section-heading">Questions ({questions.length})</h3>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>No.</th>
                <th>Section</th>
                <th>Question</th>
                <th>Marks</th>
              </tr>
            </thead>
            <tbody>
              {questions.map((q) => (
                <tr key={q.id}>
                  <td>{q.question_number}</td>
                  <td>{q.section || "-"}</td>
                  <td>{q.question_text.slice(0, 90)}{q.question_text.length > 90 ? "..." : ""}</td>
                  <td>{q.marks ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
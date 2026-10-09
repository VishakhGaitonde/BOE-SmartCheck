import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { listQuestions, getQuestionEvidence, getQuestionVerification } from "../api/papers";
import Navbar from "../components/Navbar";
import EvidenceList from "../components/EvidenceList";
import StatusBadge from "../components/StatusBadge";

export default function QuestionDetail() {
  const { paperId, questionId } = useParams();
  const [question, setQuestion] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listQuestions(paperId).then((res) => {
      const q = res.data.find((item) => item.id === Number(questionId));
      setQuestion(q);
    });

    getQuestionEvidence(paperId, questionId)
      .then((res) => setEvidence(res.data))
      .catch(() => setError("No evidence found yet. Run the verification pipeline first."));

    getQuestionVerification(paperId, questionId)
      .then((res) => setVerification(res.data))
      .finally(() => setLoading(false));
  }, [paperId, questionId]);

  if (!question) {
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
        <Link to={`/papers/${paperId}/questions`} className="back-link">
          ← Back to Question-wise Verification
        </Link>

        <div className="card">
          <div className="page-header">
            <div>
              <h2 className="card-title">Question {question.question_number}</h2>
              <p className="card-subtitle">
                {question.section || "No section"} {question.co && `· ${question.co}`} ·{" "}
                {question.marks ?? "-"} marks
              </p>
            </div>
            {verification && <StatusBadge status={verification.ai_status} />}
          </div>

          <p style={{ fontSize: 15, lineHeight: 1.6 }}>{question.question_text}</p>
        </div>

        {verification && (
          <div className="card" style={{ marginTop: 16 }}>
            <div className="evidence-block-title">AI Verification</div>
            <div style={{ display: "flex", gap: 24, marginBottom: 10, flexWrap: "wrap", fontSize: 13 }}>
              <div><strong>Syllabus match:</strong> {verification.syllabus_match ? "Yes" : "No"}</div>
              <div><strong>Textbook match:</strong> {verification.textbook_match ? "Yes" : "No"}</div>
            </div>
            {verification.syllabus_topic && (
              <p style={{ fontSize: 13, margin: "4px 0" }}>
                <strong>Syllabus topic:</strong> {verification.syllabus_topic}
              </p>
            )}
            {verification.textbook_reference && (
              <p style={{ fontSize: 13, margin: "4px 0" }}>
                <strong>Textbook reference:</strong> {verification.textbook_reference}
              </p>
            )}
            <p style={{ fontSize: 14, marginTop: 10, lineHeight: 1.5 }}>{verification.explanation}</p>
          </div>
        )}

        <h3 className="section-heading">Evidence</h3>

        {loading && <p>Loading...</p>}
        {error && <div className="alert alert-error">{error}</div>}

        {evidence && (
          <>
            <EvidenceList title="Syllabus Evidence" items={evidence.syllabus_evidence} />
            <EvidenceList title="Textbook Evidence" items={evidence.textbook_evidence} />
          </>
        )}
      </div>
    </div>
  );
}
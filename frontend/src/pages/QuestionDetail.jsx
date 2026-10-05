import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { listQuestions, getQuestionEvidence } from "../api/papers";
import Navbar from "../components/Navbar";
import EvidenceList from "../components/EvidenceList";
import StatusBadge from "../components/StatusBadge";

export default function QuestionDetail() {
  const { paperId, questionId } = useParams();
  const [question, setQuestion] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listQuestions(paperId).then((res) => {
      const q = res.data.find((item) => item.id === Number(questionId));
      setQuestion(q);
    });

    getQuestionEvidence(paperId, questionId)
      .then((res) => setEvidence(res.data))
      .catch(() => setError("No evidence found yet. Run retrieve-evidence first."))
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
            {evidence && (
              <StatusBadge
                status={evidence.syllabus_match_found ? "SUPPORTED" : "REQUIRES_BOE_REVIEW"}
              />
            )}
          </div>

          <p style={{ fontSize: 15, lineHeight: 1.6 }}>{question.question_text}</p>
        </div>

        <h3 className="section-heading">Evidence</h3>

        {loading && <p>Loading evidence...</p>}
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
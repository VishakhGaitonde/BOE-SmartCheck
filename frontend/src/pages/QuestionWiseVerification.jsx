import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { listQuestions, listVerifications } from "../api/papers";
import Navbar from "../components/Navbar";
import StatusBadge from "../components/StatusBadge";

export default function QuestionWiseVerification() {
  const { paperId } = useParams();
  const [questions, setQuestions] = useState([]);
  const [verificationsByQId, setVerificationsByQId] = useState({});
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([listQuestions(paperId), listVerifications(paperId)])
      .then(([qRes, vRes]) => {
        setQuestions(qRes.data);
        const map = {};
        vRes.data.forEach((v) => { map[v.question_id] = v; });
        setVerificationsByQId(map);
      })
      .finally(() => setLoading(false));
  }, [paperId]);

  return (
    <div>
      <Navbar />
      <div className="page">
        <Link to={`/papers/${paperId}`} className="back-link">
          ← Back to Paper Summary
        </Link>

        <div className="page-header">
          <h2>Question-wise Verification</h2>
        </div>

        {loading && <p>Loading questions...</p>}

        {!loading && (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>No.</th>
                  <th>Section</th>
                  <th>CO</th>
                  <th>Question</th>
                  <th>Marks</th>
                  <th>AI Status</th>
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => {
                  const v = verificationsByQId[q.id];
                  return (
                    <tr
                      key={q.id}
                      className="clickable"
                      onClick={() => navigate(`/papers/${paperId}/questions/${q.id}`)}
                    >
                      <td>{q.question_number}</td>
                      <td>{q.section || "-"}</td>
                      <td>{q.co || "-"}</td>
                      <td>
                        {q.question_text.slice(0, 90)}
                        {q.question_text.length > 90 ? "..." : ""}
                      </td>
                      <td>{q.marks ?? "-"}</td>
                      <td>{v ? <StatusBadge status={v.ai_status} /> : <StatusBadge status="PENDING" />}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
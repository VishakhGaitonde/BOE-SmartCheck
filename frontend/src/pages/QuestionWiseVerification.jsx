import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { listQuestions } from "../api/papers";
import Navbar from "../components/Navbar";

export default function QuestionWiseVerification() {
  const { paperId } = useParams();
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    listQuestions(paperId)
      .then((res) => setQuestions(res.data))
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
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => (
                  <tr
                    key={q.id}
                    className="clickable"
                    onClick={() => navigate(`/papers/${paperId}/questions/${q.id}`)}
                  >
                    <td>{q.question_number}</td>
                    <td>{q.section || "-"}</td>
                    <td>{q.co || "-"}</td>
                    <td>
                      {q.question_text.slice(0, 100)}
                      {q.question_text.length > 100 ? "..." : ""}
                    </td>
                    <td>{q.marks ?? "-"}</td>
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
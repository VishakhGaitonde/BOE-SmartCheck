import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import { listQuestions, listVerifications, listCoBloomResults, listBoeDecisions } from "../api/papers";
import StatusBadge from "../components/StatusBadge";

export default function QuestionWiseVerification() {
  const { paperId } = useParams();
  const [questions, setQuestions] = useState([]);
  const [verificationsByQId, setVerificationsByQId] = useState({});
  const [coBloomByQId, setCoBloomByQId] = useState({});
  const [decisionsByQId, setDecisionsByQId] = useState({});
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([listQuestions(paperId), listVerifications(paperId), listCoBloomResults(paperId), listBoeDecisions(paperId)])
      .then(([qRes, vRes, cbRes, dRes]) => {
        setQuestions(qRes.data);
        const map = {};
        vRes.data.forEach((v) => { map[v.question_id] = v; });
        setVerificationsByQId(map);
        const cbMap = {};
        cbRes.data.forEach((c) => { cbMap[c.question_id] = c; });
        setCoBloomByQId(cbMap);
        const dMap = {};
        dRes.data.forEach((d) => { dMap[d.question_id] = d; });
        setDecisionsByQId(dMap);
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
                  <th>Bloom</th>
                  <th>CO Alignment</th>
                  <th>Question</th>
                  <th>Marks</th>
                  <th>AI Status</th>
                  <th>BOE Decision</th>
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => {
                  const v = verificationsByQId[q.id];
                  const cb = coBloomByQId[q.id];
                  return (
                    <tr
                      key={q.id}
                      className="clickable"
                      onClick={() => navigate(`/papers/${paperId}/questions/${q.id}`)}
                    >
                      <td>{q.question_number}</td>
                      <td>{q.section || "-"}</td>
                      <td>{q.co || "-"}</td>
                      <td>{cb ? cb.bloom_level : "-"}</td>
                      <td>{cb ? <StatusBadge status={cb.co_alignment} /> : <StatusBadge status="PENDING" />}</td>
                      <td>
                        {q.question_text.slice(0, 70)}
                        {q.question_text.length > 70 ? "..." : ""}
                      </td>
                      <td>{q.marks ?? "-"}</td>
                      <td>{v ? <StatusBadge status={v.ai_status} /> : <StatusBadge status="PENDING" />}</td>
                      <td>
                        {decisionsByQId[q.id]
                          ? <StatusBadge status={decisionsByQId[q.id].decision} />
                          : <StatusBadge status="PENDING" />}
                      </td>
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
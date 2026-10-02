import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import FileUpload from "../components/FileUpload";
import Navbar from "../components/Navbar";
import {
  createPaper,
  uploadDocument,
  chunkDocument,
  parseQuestions,
} from "../api/papers";

const STEPS = { FORM: "FORM", UPLOADING: "UPLOADING", DONE: "DONE" };

export default function NewVerification() {
  const [courseName, setCourseName] = useState("");
  const [paperName, setPaperName] = useState("");
  const [pattern, setPattern] = useState("100");

  const [questionPaperFile, setQuestionPaperFile] = useState(null);
  const [syllabusFile, setSyllabusFile] = useState(null);
  const [textbookFile, setTextbookFile] = useState(null);

  const [step, setStep] = useState(STEPS.FORM);
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!questionPaperFile || !syllabusFile || !textbookFile) {
      setError("Please upload all three documents: question paper, syllabus, and textbook.");
      return;
    }

    setStep(STEPS.UPLOADING);

    try {
      setStatusMsg("Creating paper record...");
      const paperRes = await createPaper({
        course: courseName || null,
        paper_name: paperName,
        pattern,
      });
      const paperId = paperRes.data.id;

      setStatusMsg("Uploading syllabus...");
      const syllabusDoc = await uploadDocument(paperId, "syllabus", syllabusFile);

      setStatusMsg("Uploading textbook...");
      const textbookDoc = await uploadDocument(paperId, "textbook", textbookFile);

      setStatusMsg("Uploading question paper...");
      const qpDoc = await uploadDocument(paperId, "question_paper", questionPaperFile);

      setStatusMsg("Chunking syllabus...");
      await chunkDocument(paperId, syllabusDoc.data.id);

      setStatusMsg("Chunking textbook...");
      await chunkDocument(paperId, textbookDoc.data.id);

      setStatusMsg("Parsing question paper...");
      await parseQuestions(paperId, qpDoc.data.id);

      setStatusMsg("Done! Redirecting...");
      setStep(STEPS.DONE);
      setTimeout(() => navigate(`/papers/${paperId}`), 800);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Something went wrong during upload/processing.");
      setStep(STEPS.FORM);
    }
  };

  return (
    <div>
      <Navbar />
      <div className="page" style={{ maxWidth: 560 }}>
        <Link to="/dashboard" className="back-link">← Back to Dashboard</Link>

        <div className="card">
          <h2 className="card-title">New SEE Verification</h2>
          <p className="card-subtitle">
            Upload the question paper, syllabus, and textbook to begin verification.
          </p>

          {step === STEPS.FORM && (
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Course</label>
                <input
                  type="text"
                  className="form-input"
                  value={courseName}
                  onChange={(e) => setCourseName(e.target.value)}
                  placeholder="e.g. Database Management Systems"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Paper Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={paperName}
                  onChange={(e) => setPaperName(e.target.value)}
                  placeholder="e.g. DBMS SEE 2026"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">SEE Pattern</label>
                <select
                  className="form-select"
                  value={pattern}
                  onChange={(e) => setPattern(e.target.value)}
                >
                  <option value="50">50 Marks</option>
                  <option value="100">100 Marks</option>
                </select>
              </div>

              <FileUpload label="Question Paper" file={questionPaperFile} onChange={setQuestionPaperFile} />
              <FileUpload label="Syllabus" file={syllabusFile} onChange={setSyllabusFile} />
              <FileUpload label="Prescribed Textbook" file={textbookFile} onChange={setTextbookFile} />

              {error && <div className="alert alert-error">{error}</div>}

              <button type="submit" className="btn btn-primary btn-block">
                Verify Paper
              </button>
            </form>
          )}

          {step === STEPS.UPLOADING && (
            <div className="progress-status">
              <div className="spinner" />
              <p>{statusMsg}</p>
            </div>
          )}

          {step === STEPS.DONE && <div className="alert alert-success">✅ {statusMsg}</div>}
        </div>
      </div>
    </div>
  );
}
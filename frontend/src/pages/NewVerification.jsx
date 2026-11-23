import { useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import FileUpload from "../components/FileUpload";
import Navbar from "../components/Navbar";
import {
  createPaper,
  uploadDocument,
  checkDocuments,
  deletePaper,
  chunkDocument,
  parseQuestions,
  validateMarks,
  buildKnowledgeBase,
  buildUnitTextbookMap,
  retrieveEvidenceForPaper,
  verifyAndAnalyze,
} from "../api/papers";

const STEPS = { FORM: "FORM", UPLOADING: "UPLOADING", DONE: "DONE" };

export default function NewVerification() {
  const [courseName, setCourseName] = useState("");
  const [paperName, setPaperName] = useState("");
  const [pattern, setPattern] = useState("100");
  const [structureType, setStructureType] = useState("UNIT_OR");

  const [questionPaperFile, setQuestionPaperFile] = useState(null);
  const [syllabusFile, setSyllabusFile] = useState(null);
  const [textbookFiles, setTextbookFiles] = useState([]);

  const [step, setStep] = useState(STEPS.FORM);
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");

  const [mismatch, setMismatch] = useState(null);
  const decisionRef = useRef(null);

  const navigate = useNavigate();

  // Pauses the pipeline until the BOE presses Continue (true) or Stop (false)
  const askUser = (result) =>
    new Promise((resolve) => {
      decisionRef.current = resolve;
      setMismatch(result);
    });

  const answer = (proceed) => {
    if (decisionRef.current) {
      decisionRef.current(proceed);
      decisionRef.current = null;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!questionPaperFile || !syllabusFile || textbookFiles.length === 0) {
      setError("Please upload the question paper, the syllabus, and at least one textbook.");
      return;
    }

    setStep(STEPS.UPLOADING);

    try {
      setStatusMsg("Creating paper record...");
      const paperRes = await createPaper({
        course: courseName || null,
        paper_name: paperName,
        pattern,
        structure_type: structureType,
      });
      const paperId = paperRes.data.id;

      setStatusMsg("Uploading syllabus...");
      const syllabusDoc = await uploadDocument(paperId, "syllabus", syllabusFile);

      const textbookDocs = [];
      for (let i = 0; i < textbookFiles.length; i++) {
        setStatusMsg(`Uploading textbook ${i + 1} of ${textbookFiles.length}...`);
        textbookDocs.push(await uploadDocument(paperId, "textbook", textbookFiles[i]));
      }

      setStatusMsg("Checking that the syllabus and textbooks match the course...");
      const check = await checkDocuments(paperId);
      if (!check.data.ok) {
        const proceed = await askUser(check.data);
        setMismatch(null);
        if (!proceed) {
          await deletePaper(paperId).catch(() => {});
          setError("Stopped. Replace the file(s) that did not match and try again.");
          setStep(STEPS.FORM);
          return;
        }
      }

      setStatusMsg("Uploading question paper...");
      const qpDoc = await uploadDocument(paperId, "question_paper", questionPaperFile);

      setStatusMsg("Chunking syllabus...");
      await chunkDocument(paperId, syllabusDoc.data.id);

      for (let i = 0; i < textbookDocs.length; i++) {
        setStatusMsg(`Chunking textbook ${i + 1} of ${textbookDocs.length}...`);
        await chunkDocument(paperId, textbookDocs[i].data.id);
      }

      setStatusMsg("Parsing question paper...");
      await parseQuestions(paperId, qpDoc.data.id);

      setStatusMsg("Validating marks and sections...");
      await validateMarks(paperId);

      setStatusMsg("Building knowledge base (embedding syllabus + textbooks)...");
      await buildKnowledgeBase(paperId);

      setStatusMsg("Mapping syllabus units to textbook chapters...");
      await buildUnitTextbookMap(paperId);

      setStatusMsg("Retrieving evidence for each question...");
      await retrieveEvidenceForPaper(paperId);

      setStatusMsg("Verifying questions and analyzing CO/Bloom (combined, faster)...");
      const combinedRes = await verifyAndAnalyze(paperId);

      if (combinedRes.data.stopped_due_to_quota) {
        setStatusMsg(
          `Done — but LLM quota ran out partway (${combinedRes.data.newly_processed}/${combinedRes.data.total_questions} processed). ` +
          `You can resume later from the Paper Summary page. Redirecting...`
        );
      } else {
        setStatusMsg("Done! Redirecting...");
      }

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

      {mismatch && (
        <div className="modal-overlay">
          <div className="modal">
            <h3 className="modal-title">These files may not match</h3>
            <p className="modal-text">
              Course entered: <strong>{courseName}</strong>
            </p>

            <ul className="mismatch-list">
              {mismatch.problems.map((p, i) => (
                <li key={i}>
                  <span className="badge badge-warning">{p.kind}</span>{" "}
                  <strong>{p.filename}</strong>
                  <div className="mismatch-msg">{p.message}</div>
                </li>
              ))}
            </ul>

            {mismatch.listed_textbooks.length > 0 && (
              <>
                <p className="modal-text">Textbooks listed in the syllabus:</p>
                <ul className="listed-books">
                  {mismatch.listed_textbooks.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </>
            )}

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => answer(false)}>
                Stop
              </button>
              <button className="btn btn-primary" onClick={() => answer(true)}>
                Continue anyway
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="page" style={{ maxWidth: 560 }}>
        <Link to="/dashboard" className="back-link">← Back to Dashboard</Link>

        <div className="card">
          <h2 className="card-title">New SEE Verification</h2>
          <p className="card-subtitle">
            Upload the question paper, syllabus, and textbook(s) to begin verification.
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
                  placeholder="e.g. Digital Design and Computer Organization"
                  required
                />
                <p className="form-hint">
                  Type the course name as it appears in the syllabus. It is used to check the uploaded files.
                </p>
              </div>

              <div className="form-group">
                <label className="form-label">Paper Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={paperName}
                  onChange={(e) => setPaperName(e.target.value)}
                  placeholder="e.g. DDCO SEE 2026"
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

              <div className="form-group">
                <label className="form-label">Paper Structure</label>
                <select
                  className="form-select"
                  value={structureType}
                  onChange={(e) => setStructureType(e.target.value)}
                >
                  <option value="UNIT_OR">Unit-wise (OR choice per unit)</option>
                  <option value="SECTION_EQUAL">Section A–E (equal marks)</option>
                </select>
                <p className="form-hint">
                  Choose "Unit-wise" for papers with "Answer one full question from each unit"
                  style OR choices. Choose "Section A–E" for fixed-section papers.
                </p>
              </div>

              <FileUpload label="Question Paper" file={questionPaperFile} onChange={setQuestionPaperFile} />
              <FileUpload label="Syllabus" file={syllabusFile} onChange={setSyllabusFile} />
              <FileUpload
                label="Prescribed Textbook(s)"
                file={textbookFiles}
                onChange={setTextbookFiles}
                multiple
              />
              <p className="form-hint" style={{ marginTop: -10, marginBottom: 16 }}>
                You can add more than one textbook. Pick the files one after another or select several at once.
              </p>

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
import client from "./client";

export const createPaper = (data) => client.post("/papers", data);

export const listPapers = () => client.get("/papers");

export const getPaper = (paperId) => client.get(`/papers/${paperId}`);

export const uploadDocument = (paperId, documentType, file) => {
  const formData = new FormData();
  formData.append("document_type", documentType);
  formData.append("file", file);
  return client.post(`/papers/${paperId}/documents`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const listDocuments = (paperId) =>
  client.get(`/papers/${paperId}/documents`);

export const chunkDocument = (paperId, documentId) =>
  client.post(`/papers/${paperId}/documents/${documentId}/chunk`);

export const parseQuestions = (paperId, documentId) =>
  client.post(`/papers/${paperId}/documents/${documentId}/parse-questions`);

export const listQuestions = (paperId) =>
  client.get(`/papers/${paperId}/questions`);

export const validateMarks = (paperId) =>
  client.post(`/papers/${paperId}/validate-marks`);

export const getValidation = (paperId) =>
  client.get(`/papers/${paperId}/validate-marks`);

export const retrieveEvidence = (paperId, topK = 5) =>
  client.post(`/papers/${paperId}/retrieve-evidence`, null, {
    params: { top_k: topK },
  });

export const getQuestionEvidence = (paperId, questionId) =>
  client.get(`/papers/${paperId}/questions/${questionId}/evidence`);

export const buildKnowledgeBase = (paperId) =>
  client.post(`/papers/${paperId}/build-knowledge-base`);

export const retrieveEvidenceForPaper = (paperId, topK = 5) =>
  client.post(`/papers/${paperId}/retrieve-evidence`, null, {
    params: { top_k: topK },
  });

export const buildUnitTextbookMap = (paperId) =>
  client.post(`/papers/${paperId}/build-unit-textbook-map`);

export const getQuestionVerification = (paperId, questionId) =>
  client.get(`/papers/${paperId}/questions/${questionId}/verification`);

export const verifyQuestions = (paperId, force = false) =>
  client.post(`/papers/${paperId}/verify-questions`, null, { params: { force } });

export const listVerifications = (paperId) =>
  client.get(`/papers/${paperId}/verifications`);

export const analyzeCoBloom = (paperId) =>
  client.post(`/papers/${paperId}/analyze-co-bloom`);

export const listCoBloomResults = (paperId) =>
  client.get(`/papers/${paperId}/co-bloom-results`);

export const verifyAndAnalyze = (paperId, force = false) =>
  client.post(`/papers/${paperId}/verify-and-analyze`, null, { params: { force } });

export const saveBoeDecision = (paperId, questionId, decision, comment) =>
  client.put(`/papers/${paperId}/questions/${questionId}/decision`, { decision, comment });

export const getBoeDecision = (paperId, questionId) =>
  client.get(`/papers/${paperId}/questions/${questionId}/decision`);

export const listBoeDecisions = (paperId) =>
  client.get(`/papers/${paperId}/decisions`);

export const getDecisionSummary = (paperId) =>
  client.get(`/papers/${paperId}/decisions/summary`);

export const detectDuplicates = (paperId) =>
  client.post(`/papers/${paperId}/detect-duplicates`);

export const listDuplicates = (paperId) =>
  client.get(`/papers/${paperId}/duplicates`);

export const aggregateSummary = (paperId) =>
  client.post(`/papers/${paperId}/aggregate-summary`);

export const getPaperCoordinatorSummary = (paperId) =>
  client.get(`/papers/${paperId}/summary`);

export const downloadReport = async (paperId, paperName) => {
  const res = await client.get(`/papers/${paperId}/report`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `${paperName || "paper"}_report.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
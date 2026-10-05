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
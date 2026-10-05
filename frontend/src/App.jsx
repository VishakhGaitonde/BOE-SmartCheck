import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import NewVerification from "./pages/NewVerification";
import PaperSummary from "./pages/PaperSummary";
import QuestionWiseVerification from "./pages/QuestionWiseVerification";
import QuestionDetail from "./pages/QuestionDetail";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/new-verification" element={<ProtectedRoute><NewVerification /></ProtectedRoute>} />
          <Route path="/papers/:paperId" element={<ProtectedRoute><PaperSummary /></ProtectedRoute>} />
          <Route path="/papers/:paperId/questions" element={<ProtectedRoute><QuestionWiseVerification /></ProtectedRoute>} />
          <Route path="/papers/:paperId/questions/:questionId" element={<ProtectedRoute><QuestionDetail /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
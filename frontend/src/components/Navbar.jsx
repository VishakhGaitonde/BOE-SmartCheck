import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Navbar() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="navbar">
      <div className="navbar-brand">
        <span className="dot" />
        BOE SmartCheck
      </div>
      <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
}
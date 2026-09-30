import { useAuth } from "../auth/AuthContext";

export default function Dashboard() {
  const { logout } = useAuth();

  return (
    <div style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h2>Dashboard</h2>
      <p>You are logged in.</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AdminAuth } from "../lib/api";

function AdminLogin() {
  const [password, setPassword] = useState(AdminAuth.get());
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!password) {
      setError("Password is required");
      return;
    }
    AdminAuth.set(password);
    navigate("/admin/dashboard");
  };

  return (
    <div className="max-w-xl mx-auto glass-card p-8 space-y-5">
      <div className="space-y-2">
        <div className="glow-pill text-secondary">
          <span>🔐</span>
          <span>Admin access</span>
        </div>
        <h1 className="text-3xl font-semibold">Unlock the control room</h1>
        <p className="text-slate-300 text-sm">
          Enter the admin password configured on the server. All admin actions use header-based authentication.
        </p>
      </div>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm text-slate-200 space-y-2">
          <span>Password</span>
          <input
            type="password"
            className="w-full rounded-2xl bg-black/30 border border-white/10 px-4 py-3 text-white"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && <p className="text-sm text-rose-400">{error}</p>}
        <button type="submit" className="button primary w-full">
          Access dashboard
        </button>
      </form>
    </div>
  );
}

export default AdminLogin;

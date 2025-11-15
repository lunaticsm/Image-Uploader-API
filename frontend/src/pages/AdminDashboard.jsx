import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { AdminAuth, fetchJson } from "../lib/api";
import AnimatedNumber from "../components/AnimatedNumber";
import { formatBytes, formatNumber } from "../lib/formatters";

function AdminDashboard() {
  const navigate = useNavigate();
  const [password, setPassword] = useState(AdminAuth.get());
  const [summary, setSummary] = useState(null);
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const headers = password ? { "X-Admin-Password": password } : {};

  const ensurePassword = useCallback(() => {
    if (!password) {
      navigate("/admin/login");
      return false;
    }
    return true;
  }, [password, navigate]);

  const loadData = useCallback(async () => {
    if (!ensurePassword()) return;
    setLoading(true);
    setError("");
    try {
      const [summaryData, filesData] = await Promise.all([
        fetchJson("/api/admin/summary", { headers }),
        fetchJson("/api/admin/files", { headers }),
      ]);
      setSummary(summaryData);
      setFiles(filesData.files || []);
    } catch (err) {
      setError(err.message);
      if (err.message.toLowerCase().includes("password")) {
        AdminAuth.clear();
        setPassword("");
        navigate("/admin/login");
      }
    } finally {
      setLoading(false);
    }
  }, [headers, ensurePassword, navigate, password]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDelete = async (fileId) => {
    if (!ensurePassword()) return;
    try {
      await fetchJson(`/api/admin/files/${encodeURIComponent(fileId)}`, {
        method: "DELETE",
        headers,
      });
      setMessage("File removed 🗑️");
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteAll = async () => {
    if (!ensurePassword()) return;
    if (!window.confirm("Delete ALL files? This cannot be undone.")) return;
    try {
      await fetchJson("/api/admin/files", {
        method: "DELETE",
        headers,
      });
      setMessage("All files deleted 🧼");
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    AdminAuth.clear();
    setPassword("");
    navigate("/admin/login");
  };

  const summaryCards = summary
    ? [
        { label: "Uploads", value: summary.uploads, icon: "📁", formatter: formatNumber },
        { label: "Downloads", value: summary.downloads, icon: "📥", formatter: formatNumber },
        { label: "Deleted", value: summary.deleted, icon: "🧹", formatter: formatNumber },
        { label: "Storage", value: summary.storage_bytes || 0, icon: "💾", formatter: formatBytes },
      ]
    : [];

  return (
    <div className="space-y-8">
      <div className="glass-card p-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-secondary">Admin Dashboard</p>
          <h1 className="text-2xl font-semibold">Control room 🛠️</h1>
        </div>
        <div className="flex gap-2">
          <button className="button secondary" onClick={loadData} disabled={loading}>
            Refresh
          </button>
          <button className="button secondary" onClick={handleLogout}>
            Logout
          </button>
          <button className="button primary" onClick={handleDeleteAll}>
            Delete All
          </button>
        </div>
      </div>

      {message && <p className="text-sm text-emerald-300">{message}</p>}
      {error && <p className="text-sm text-rose-400">{error}</p>}

      {summary && (
        <section className="grid gap-4 md:grid-cols-4">
          {summaryCards.map((item) => (
            <div key={item.label} className="metric-card">
              <span className="label">{item.icon} {item.label}</span>
              <AnimatedNumber value={item.value} format={item.formatter} />
            </div>
          ))}
        </section>
      )}

      <section className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Recent uploads</h2>
          <span className="text-sm text-slate-400">{files.length} files</span>
        </div>
        <div className="overflow-x-auto">
          <table className="table-modern">
            <thead>
              <tr>
                <th>ID</th>
                <th>Filename</th>
                <th>Size</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {files.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-4 text-center text-slate-500">
                    {loading ? "Loading…" : "No files yet"}
                  </td>
                </tr>
              )}
              {files.map((file) => (
                <tr key={file.id}>
                  <td className="font-mono text-xs text-slate-400">{file.id}</td>
                  <td>{file.name}</td>
                  <td>{formatBytes(file.size)}</td>
                  <td>{new Date(file.created_at).toLocaleString()}</td>
                  <td>
                    <button className="text-rose-300 text-sm" onClick={() => handleDelete(file.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default AdminDashboard;

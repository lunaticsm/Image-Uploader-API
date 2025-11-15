import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { AdminAuth, fetchJson } from "../lib/api";
import AnimatedNumber from "../components/AnimatedNumber";
import { formatBytes, formatNumber } from "../lib/formatters";
import LoadingSpinner from "../components/LoadingSpinner";
import Skeleton from "../components/Skeleton";

function AdminDashboard() {
  const navigate = useNavigate();
  const [password, setPassword] = useState(AdminAuth.get());
  const [summary, setSummary] = useState(null);
  const [files, setFiles] = useState([]);
  const [deletingFiles, setDeletingFiles] = useState(new Set());
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const headers = useMemo(() => password ? { "X-Admin-Password": password } : {}, [password]);

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
  }, [headers, ensurePassword, navigate]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Cleanup deletingFiles after a timeout to ensure they're properly cleared
  useEffect(() => {
    if (deletingFiles.size > 0) {
      const timeoutId = setTimeout(() => {
        setDeletingFiles(new Set());
      }, 1000); // Clear after 1 second, which should be enough for the animation

      return () => clearTimeout(timeoutId);
    }
  }, [deletingFiles]);

  const handleDelete = async (fileId) => {
    if (!ensurePassword()) return;

    try {
      // Add visual feedback - mark file for deletion (fade out animation)
      setDeletingFiles(prev => new Set([...prev, fileId]));

      await fetchJson(`/api/admin/files/${encodeURIComponent(fileId)}`, {
        method: "DELETE",
        headers,
      });

      setMessage("File removed 🗑️");
      loadData();
      // The row will be removed from the UI when loadData() refreshes the list
    } catch (err) {
      setError(err.message);
      // If deletion fails, remove the file from the deleting state
      setDeletingFiles(prev => {
        const newSet = new Set(prev);
        newSet.delete(fileId);
        return newSet;
      });
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
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
          <button
            className="button secondary hover:scale-105 transition-transform duration-200 ripple px-4 py-2 sm:px-6"
            onClick={loadData}
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Loading...
              </span>
            ) : "Refresh"}
          </button>
          <button
            className="button secondary hover:scale-105 transition-transform duration-200 ripple px-4 py-2 sm:px-6"
            onClick={handleLogout}
          >
            Logout
          </button>
          <button
            className="button primary hover:scale-105 transition-transform duration-200 ripple px-4 py-2 sm:px-6"
            onClick={handleDeleteAll}
          >
            Delete All
          </button>
        </div>
      </div>

      {message && <p className="text-sm text-emerald-300 animate-fadeIn">{message}</p>}
      {error && <p className="text-sm text-rose-400 animate-fadeIn">{error}</p>}

      {summary ? (
        <section className="grid gap-4 md:grid-cols-4">
          {summaryCards.map((item, index) => (
            <div
              key={item.label}
              className="metric-card animate-fadeInSlideUp"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <span className="label">{item.icon} {item.label}</span>
              <AnimatedNumber value={item.value} format={item.formatter} />
            </div>
          ))}
        </section>
      ) : (
        <section className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </section>
      )}

      <section className="glass-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Recent uploads</h2>
            <p className="text-sm text-slate-400">{files.length} files</p>
          </div>
        </div>
        <div className="overflow-x-auto rounded-lg">
          <table className="table-modern w-full">
            <thead className="bg-white/5">
              <tr>
                <th className="text-left">ID</th>
                <th className="text-left">Filename</th>
                <th className="text-left">Size</th>
                <th className="text-left">Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && files.length === 0 ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <tr key={`skeleton-${index}`} className="animate-pulse">
                    <td className="py-4"><Skeleton className="h-4 w-16" /></td>
                    <td><Skeleton className="h-4 w-full max-w-[120px]" /></td>
                    <td><Skeleton className="h-4 w-12" /></td>
                    <td><Skeleton className="h-4 w-20" /></td>
                    <td className="text-right"><Skeleton className="h-6 w-16 ml-auto" /></td>
                  </tr>
                ))
              ) : files.length === 0 ? (
                <tr>
                  <td colSpan="5" className="py-12 text-center text-slate-500">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <span className="text-4xl">📭</span>
                      <span>No files yet</span>
                      <p className="text-sm text-slate-400">Upload files to see them appear here</p>
                    </div>
                  </td>
                </tr>
              ) : (
                files.map((file, index) => (
                  <tr
                    key={file.id}
                    data-file-id={file.id}
                    className={`hover:bg-white/5 transition-all duration-200 animate-fadeInSlideUp border-b border-white/5 last:border-0 ${
                      deletingFiles.has(file.id)
                        ? 'opacity-0 -translate-x-5 transition-all duration-300 ease-in-out'
                        : 'transition-all duration-200'
                    }`}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <td className="font-mono text-xs text-slate-400 py-3 max-w-[100px] truncate" title={file.id}>{file.id}</td>
                    <td className="py-3 max-w-[200px] truncate" title={file.name}>{file.name}</td>
                    <td className="py-3">{formatBytes(file.size)}</td>
                    <td className="py-3">{new Date(file.created_at).toLocaleDateString()}</td>
                    <td className="py-3 text-right">
                      <button
                        className="text-rose-300 text-sm hover:text-rose-200 hover:scale-110 transition-all duration-200 ripple px-3 py-1 rounded-md hover:bg-rose-500/10 disabled:opacity-50"
                        onClick={() => handleDelete(file.id)}
                        title={`Delete ${file.name}`}
                        disabled={deletingFiles.has(file.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default AdminDashboard;

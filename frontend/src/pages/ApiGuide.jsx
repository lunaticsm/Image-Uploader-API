const endpoints = [
  {
    method: "POST",
    path: "/upload",
    description: "Multipart `file` field. Returns JSON metadata (`id`, `url`, `size`, `type`).",
  },
  {
    method: "POST",
    path: "/upload-permanent",
    description: "Same payload but requires API key. Marks files as permanent (excluded from cleanup).",
  },
  {
    method: "GET",
    path: "/{filename}",
    description: "Serves stored file with CDN-friendly cache headers.",
  },
  {
    method: "GET",
    path: "/metrics",
    description: "Live counters for uploads, downloads, deletions, and storage usage.",
  },
];

function ApiGuide() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <section className="glass-card p-8 space-y-4">
        <div className="glow-pill text-secondary">
          <span>📘</span>
          <span>REST reference</span>
        </div>
        <h1 className="text-3xl font-semibold">AlterBase CDN API</h1>
        <p className="text-slate-300">
          Upload files and retrieve shareable URLs with a minimal HTTP API. Each client is rate-limited per minute, and uploads are capped based on your environment.
        </p>
        <div className="text-xs uppercase tracking-[0.3em] text-slate-500">Base URL</div>
        <pre className="code-block">
          <code>https://cdn.alterbase.web.id</code>
        </pre>
      </section>

      <section className="glass-card p-8 space-y-4">
        <div className="glow-pill">
          <span>🛠️</span>
          <span>Endpoints</span>
        </div>
        <h2 className="section-title">Endpoints</h2>
        <div className="space-y-3">
          {endpoints.map((endpoint) => (
            <article key={endpoint.path} className="endpoint-card">
              <div className="endpoint-verb">{endpoint.method}</div>
              <div>
                <strong className="text-lg">{endpoint.path}</strong>
                <p className="text-sm text-slate-300">{endpoint.description}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="glass-card p-8 space-y-3">
        <div className="glow-pill">
          <span>🔐</span>
          <span>Authentication</span>
        </div>
        <h2 className="section-title">Authentication</h2>
        <p className="text-sm text-slate-300">For permanent uploads, include your API key:</p>
        <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
          <li>
            <code>X-API-Key: your-api-key</code>
          </li>
          <li>
            <code>?api_key=your-api-key</code>
          </li>
        </ul>
      </section>

      <section className="glass-card p-8 space-y-3">
        <div className="glow-pill">
          <span>💻</span>
          <span>cURL Example</span>
        </div>
        <h2 className="section-title">cURL Example</h2>
        <pre className="code-block">
          <code>
            curl -X POST https://cdn.alterbase.web.id/upload \
            {`\n  -F "file=@/path/to/photo.jpg" \\`}{`\n  -H "Accept: application/json"`}
          </code>
        </pre>
      </section>

      <section className="glass-card p-8 space-y-3">
        <div className="glow-pill">
          <span>📝</span>
          <span>Notes</span>
        </div>
        <h2 className="section-title">Notes</h2>
        <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
          <li>Files land in <code>UPLOAD_DIR</code> and optionally mirror to MEGA.</li>
          <li>The cleaner removes items older than <code>DELETE_AFTER_HOURS</code> once backups complete.</li>
          <li>Use the relative URLs from responses (e.g. <code>/abc123.jpg</code>) with your CDN hostname.</li>
        </ul>
      </section>
    </div>
  );
}

export default ApiGuide;

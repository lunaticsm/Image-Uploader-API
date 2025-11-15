import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

// Register the ScrollTrigger plugin
gsap.registerPlugin(ScrollTrigger);

// API configuration with environment fallback
const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_BASE_URL || 'https://cdn.alterbase.web.id'
};

const endpoints = [
  {
    method: "POST",
    path: "/upload",
    description: "Multipart `file` field. Returns JSON metadata (`id`, `url`, `size`, `type`).",
    requestExample: `curl -X POST \${API_CONFIG.BASE_URL}/upload \\
  -F "file=@/path/to/photo.jpg" \\
  -H "Accept: application/json"`,
    responseExample: `{
  "id": "abc123.jpg",
  "url": "/abc123.jpg",
  "size": 123456,
  "type": "image/jpeg",
  "created_at": "2023-01-01T00:00:00Z"
}`,
    statusCodes: [
      { code: 200, description: "File uploaded successfully" },
      { code: 400, description: "Invalid file format or missing file" },
      { code: 413, description: "File too large" },
      { code: 429, description: "Rate limit exceeded" }
    ]
  },
  {
    method: "POST",
    path: "/upload-permanent",
    description: "Same payload as /upload but requires API key. Marks files as permanent (excluded from cleanup).",
    requestExample: `curl -X POST \${API_CONFIG.BASE_URL}/upload-permanent \\
  -F "file=@/path/to/photo.jpg" \\
  -H "X-API-Key: your-api-key" \\
  -H "Accept: application/json"`,
    responseExample: `{
  "id": "def456.jpg",
  "url": "/def456.jpg",
  "size": 789012,
  "type": "image/png",
  "permanent": true,
  "created_at": "2023-01-01T00:00:00Z"
}`,
    statusCodes: [
      { code: 200, description: "File uploaded successfully as permanent" },
      { code: 400, description: "Invalid file format or missing file" },
      { code: 401, description: "Missing or invalid API key" },
      { code: 403, description: "Insufficient permissions" },
      { code: 413, description: "File too large" },
      { code: 429, description: "Rate limit exceeded" }
    ]
  },
  {
    method: "GET",
    path: "/{filename}",
    description: "Serves stored file with CDN-friendly cache headers.",
    requestExample: `curl -X GET \${API_CONFIG.BASE_URL}/abc123.jpg`,
    responseExample: `// Binary file content with appropriate Content-Type header`,
    statusCodes: [
      { code: 200, description: "File found and served" },
      { code: 404, description: "File not found" },
      { code: 410, description: "File has been deleted" }
    ]
  },
  {
    method: "GET",
    path: "/metrics",
    description: "Live counters for uploads, downloads, deletions, and storage usage.",
    requestExample: `curl -X GET \${API_CONFIG.BASE_URL}/metrics \\
  -H "Accept: application/json"`,
    responseExample: `{
  "uploads": 12345,
  "downloads": 67890,
  "deleted": 123,
  "storage_bytes": 1073741824
}`,
    statusCodes: [
      { code: 200, description: "Metrics retrieved successfully" },
      { code: 500, description: "Internal server error" }
    ]
  },
];

function ApiGuide() {
  const sectionRefs = useRef([]);

  useEffect(() => {
    // Animate sections on load
    sectionRefs.current.forEach((el, index) => {
      if (el) {
        gsap.fromTo(el,
          { opacity: 0, y: 30 },
          {
            opacity: 1,
            y: 0,
            duration: 0.8,
            ease: "power2.out",
            delay: index * 0.1,
            scrollTrigger: {
              trigger: el,
              start: "top 85%",
            }
          }
        );
      }
    });

    // Add hover animations to endpoint cards
    const cards = document.querySelectorAll('.endpoint-card');
    cards.forEach(card => {
      const handleMouseEnter = () => {
        gsap.to(card, {
          x: 5,
          boxShadow: "0 10px 25px rgba(56, 189, 248, 0.2)",
          duration: 0.3,
          ease: "power2.out"
        });
      };

      const handleMouseLeave = () => {
        gsap.to(card, {
          x: 0,
          boxShadow: "0 4px 6px rgba(0, 0, 0, 0.05)",
          duration: 0.3,
          ease: "power2.out"
        });
      };

      card.addEventListener('mouseenter', handleMouseEnter);
      card.addEventListener('mouseleave', handleMouseLeave);

      return () => {
        card.removeEventListener('mouseenter', handleMouseEnter);
        card.removeEventListener('mouseleave', handleMouseLeave);
      };
    });
  }, []);

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <section ref={el => sectionRefs.current[0] = el} className="glass-card p-8 space-y-4 animate-fadeInSlideUp">
        <div className="glow-pill text-secondary">
          <span>📘</span>
          <span>REST reference</span>
        </div>
        <h1 className="text-3xl font-semibold">AlterBase CDN API</h1>
        <p className="text-slate-300">
          Upload files and retrieve shareable URLs with a minimal HTTP API. Each client is rate-limited per minute, and uploads are capped based on your environment.
        </p>
        <div className="text-xs uppercase tracking-[0.3em] text-slate-500">Base URL</div>
        <pre className="code-block animate-pulse-slow">
          <code>{API_CONFIG.BASE_URL}</code>
        </pre>
      </section>

      <section ref={el => sectionRefs.current[1] = el} className="glass-card p-8 space-y-4 animate-fadeInSlideUp" style={{ animationDelay: '100ms' }}>
        <div className="glow-pill">
          <span>🛠️</span>
          <span>Endpoints</span>
        </div>
        <h2 className="section-title">Endpoints</h2>
        <div className="space-y-3">
          {endpoints.map((endpoint, index) => (
            <article
              key={endpoint.path}
              className="endpoint-card hover:scale-[1.02] transition-all duration-300 animate-fadeInSlideUp bg-white/5 p-4 rounded-lg"
              style={{ animationDelay: `${index * 50 + 150}ms` }}
            >
              <div className="flex flex-col sm:flex-row sm:items-start gap-3">
                <div className={`endpoint-verb text-center rounded-md px-3 py-1 text-sm font-mono min-w-[80px] ${
                  endpoint.method === 'GET' ? 'bg-blue-500/20 text-blue-300' :
                  endpoint.method === 'POST' ? 'bg-green-500/20 text-green-300' :
                  endpoint.method === 'DELETE' ? 'bg-rose-500/20 text-rose-300' : 'bg-purple-500/20 text-purple-300'
                }`}>
                  {endpoint.method}
                </div>
                <div className="flex-1">
                  <div className="font-mono text-[#fbbf24] text-lg break-all">{endpoint.path}</div>
                  <p className="text-sm text-slate-300 mt-1">{endpoint.description}</p>

                  {/* Request Example */}
                  {endpoint.requestExample && (
                    <div className="mt-3">
                      <div className="text-xs uppercase tracking-[0.1em] text-slate-400 mb-1">REQUEST EXAMPLE</div>
                      <pre className="code-block text-xs overflow-x-auto">
                        <code>{endpoint.requestExample}</code>
                      </pre>
                    </div>
                  )}

                  {/* Response Example */}
                  {endpoint.responseExample && (
                    <div className="mt-3">
                      <div className="text-xs uppercase tracking-[0.1em] text-slate-400 mb-1">RESPONSE EXAMPLE</div>
                      <pre className="code-block text-xs overflow-x-auto">
                        <code>{endpoint.responseExample}</code>
                      </pre>
                    </div>
                  )}

                  {/* Status Codes */}
                  {endpoint.statusCodes && endpoint.statusCodes.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs uppercase tracking-[0.1em] text-slate-400 mb-1">STATUS CODES</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {endpoint.statusCodes.map((status, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-xs">
                            <span className={`px-2 py-1 rounded ${
                              status.code === 200 ? 'bg-emerald-500/20 text-emerald-400' :
                              status.code >= 400 && status.code < 500 ? 'bg-amber-500/20 text-amber-400' :
                              'bg-rose-500/20 text-rose-400'
                            }`}>
                              {status.code}
                            </span>
                            <span className="text-slate-300">{status.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section ref={el => sectionRefs.current[2] = el} className="glass-card p-8 space-y-3 animate-fadeInSlideUp" style={{ animationDelay: '200ms' }}>
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

      <section ref={el => sectionRefs.current[3] = el} className="glass-card p-8 space-y-3 animate-fadeInSlideUp" style={{ animationDelay: '250ms' }}>
        <div className="glow-pill">
          <span>💻</span>
          <span>cURL Example</span>
        </div>
        <h2 className="section-title">cURL Example</h2>
        <pre className="code-block">
          <code>
            curl -X POST {API_CONFIG.BASE_URL}/upload \
            {`\n  -F "file=@/path/to/photo.jpg" \\`}{`\n  -H "Accept: application/json"`}
          </code>
        </pre>
      </section>

      <section ref={el => sectionRefs.current[4] = el} className="glass-card p-8 space-y-3 animate-fadeInSlideUp" style={{ animationDelay: '300ms' }}>
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

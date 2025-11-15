import { useMemo } from "react";
import { Link } from "react-router-dom";

function NotFound() {
  const particles = useMemo(
    () => Array.from({ length: 6 }, () => ({ top: `${Math.random() * 100}%`, left: `${Math.random() * 100}%` })),
    [],
  );

  return (
    <div className="max-w-3xl mx-auto text-center space-y-8">
      <div className="glass-card p-12 space-y-6 relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none opacity-70">
          <div className="h-full bg-[radial-gradient(circle_at_30%_20%,rgba(248,250,252,0.1),transparent_60%),radial-gradient(circle_at_70%_0%,rgba(59,130,246,0.2),transparent_55%)]" />
        </div>
        <div className="glow-pill mx-auto w-fit">
          <span>🚧</span>
          <span>Page not found</span>
        </div>
        <div className="sparkle">
          {particles.map((pos, index) => (
            <span key={index} style={pos} />
          ))}
        </div>
        <p className="text-7xl relative">🛰️</p>
        <h1 className="text-4xl font-semibold relative">Signal lost</h1>
        <p className="text-slate-300 text-base relative">
          That route isn’t part of the new dashboard. Grab a fresh link or head back home.
        </p>
        <div className="flex flex-wrap justify-center gap-4 relative">
          <Link className="button primary" to="/">
            Take me home
          </Link>
          <Link className="button secondary" to="/api-guide">
            API guide
          </Link>
        </div>
      </div>
      <p className="text-sm text-slate-500">
        Need help? Email{" "}
        <a className="underline text-secondary" href="mailto:admin@alterbase.web.id">
          admin@alterbase.web.id
        </a>
        .
      </p>
    </div>
  );
}

export default NotFound;

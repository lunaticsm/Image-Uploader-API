import { NavLink, Outlet } from "react-router-dom";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/api-guide", label: "API Guide" },
  { href: "/admin/dashboard", label: "Admin" },
];

function Layout() {
  return (
    <div className="app-shell">
      <header className="px-6 py-6 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <span className="h-4 w-4 rounded-full bg-gradient-to-r from-[#fcd34d] to-[#fb7185] shadow-brand" />
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-300">AlterBase CDN</p>
            <p className="text-slate-400 text-sm">Ultra-fast upload stack • MEGA mirror • zero drama</p>
          </div>
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-end md:gap-4">
          <nav className="flex flex-wrap gap-2 text-sm relative">
            {navLinks.map((link) => (
              <NavLink
                key={link.href}
                to={link.href}
                className={({ isActive }) =>
                  [
                    "nav-chip px-4 py-2 rounded-full border transition relative overflow-hidden",
                    isActive ? "border-white/70 text-white shadow-lg shadow-white/10 nav-chip-active" : "border-white/15 text-slate-300 hover:text-white",
                  ].join(" ")
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <a
            className="button primary text-sm text-center"
            href="https://github.com/lunaticsm/Image-Uploader-API"
            rel="noopener"
          >
            Launch on GitHub
          </a>
        </div>
      </header>
      <main className="content-area px-6 pb-12">
        <Outlet />
      </main>
      <footer className="px-6 py-8 text-center text-xs text-slate-500 space-y-1">
        <p>
          Made with <span className="text-rose-400">♥</span> by lunaticsm
        </p>
        <p>© {new Date().getFullYear()} AlterBase CDN</p>
      </footer>
    </div>
  );
}

export default Layout;

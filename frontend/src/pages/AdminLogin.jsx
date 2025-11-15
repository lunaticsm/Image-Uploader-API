import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { AdminAuth } from "../lib/api";
import { gsap } from 'gsap';

function AdminLogin() {
  const [password, setPassword] = useState(AdminAuth.get());
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const formRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    // Animate the form on load
    if (formRef.current) {
      gsap.fromTo(formRef.current,
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, duration: 0.8, ease: "power2.out", delay: 0.2 }
      );
    }

    // Animate the input field
    if (inputRef.current) {
      setTimeout(() => {
        if (inputRef.current) {
          gsap.fromTo(inputRef.current,
            { scale: 0.95, opacity: 0 },
            { scale: 1, opacity: 1, duration: 0.6, ease: "back.out(1.7)" }
          );
        }
      }, 300);
    }
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!password) {
      setError("Password is required");
      return;
    }

    setIsSubmitting(true);
    setError("");

    // Simulate API delay for visual feedback
    setTimeout(() => {
      try {
        AdminAuth.set(password);
        navigate("/admin/dashboard");
      } catch (e) {
        setError("Invalid password");
        setIsSubmitting(false);
      }
    }, 500);
  };

  return (
    <div className="max-w-md mx-auto glass-card p-8 space-y-6">
      <div ref={formRef} className="space-y-4">
        <div className="text-center animate-fadeIn">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-r from-[#fb7185] to-[#f97316] mb-4">
            <span className="text-2xl">🔐</span>
          </div>
          <h1 className="text-2xl font-semibold">Admin Access</h1>
          <p className="text-slate-400 text-sm mt-1">
            Secure access to the control panel
          </p>
        </div>

        <div className="animate-fadeIn" style={{ animationDelay: '0.1s' }}>
          <p className="text-slate-300 text-sm text-center">
            Enter the admin password configured on the server
          </p>
        </div>
      </div>

      <form className="space-y-5 animate-fadeIn" style={{ animationDelay: '0.2s' }} onSubmit={handleSubmit}>
        <div>
          <label className="block text-sm text-slate-200 mb-2">
            Admin Password
          </label>
          <div className="relative">
            <input
              ref={inputRef}
              type="password"
              className="w-full rounded-xl bg-black/30 border border-white/10 px-4 py-3 text-white focus:ring-2 focus:ring-[#fb7185] focus:border-transparent transition-all duration-300 pl-10"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password..."
            />
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400">
              🔑
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-3 animate-fadeIn">
            <p className="text-sm text-rose-400 flex items-center gap-2">
              <span>⚠️</span> {error}
            </p>
          </div>
        )}

        <button
          type="submit"
          className="button primary w-full hover:scale-105 transition-transform duration-200 relative overflow-hidden"
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
              Verifying...
            </span>
          ) : (
            "Access Dashboard →"
          )}
        </button>
      </form>
    </div>
  );
}

export default AdminLogin;

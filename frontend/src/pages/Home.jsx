import { Link } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import { gsap } from "gsap";
import anime from "animejs";
import AnimatedNumber from "../components/AnimatedNumber";
import { fetchJson } from "../lib/api";
import { formatBytes, formatNumber } from "../lib/formatters";
import LoadingSpinner from "../components/LoadingSpinner";
import MetricBarChart from "../components/MetricBarChart";
import AdvancedMetricVisualization from "../components/AdvancedMetricVisualization";

const defaultMetrics = { uploads: 0, downloads: 0, deleted: 0, storage_bytes: 0 };
const sparkles = Array.from({ length: 8 });

const workflow = [
  {
    step: "01",
    title: "Upload",
    body: "Send multipart payloads to /upload and get sharable slugs instantly.",
  },
  {
    step: "02",
    title: "Mirror",
    body: "Background worker mirrors each file to MEGA for resilience.",
  },
  {
    step: "03",
    title: "Clean",
    body: "Scheduler prunes expired files only after remote copies exist.",
  },
];

const highlights = [
  { emoji: "🧱", title: "Public API", text: "Upload, list, download, and fetch metrics via JSON endpoints." },
  { emoji: "📊", title: "Admin dashboard", text: "React UI with password-protected controls and live stats." },
  { emoji: "☁️", title: "MEGA backup", text: "Configure once and every file gets remote redundancy automatically." },
];

const infoHighlights = [
  { icon: "⚡", text: "Uploads stream directly to disk; mirror kicks off immediately." },
  { icon: "🛡️", text: "Cleaner only removes files that are safely backed up." },
  { icon: "📈", text: "Metrics endpoint keeps your status page honest." },
];

function HomePage() {
  const [metrics, setMetrics] = useState(defaultMetrics);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastSuccessfulUpdate, setLastSuccessfulUpdate] = useState(null);
  const sparklePositions = useMemo(
    () => sparkles.map(() => ({ top: `${Math.random() * 100}%`, left: `${Math.random() * 100}%` })),
    [],
  );
  const floatingNodes = useMemo(
    () =>
      Array.from({ length: 6 }, () => ({
        top: `${Math.random() * 70 + 10}%`,
        left: `${Math.random() * 70 + 10}%`,
        size: Math.random() * 30 + 20,
        delay: Math.random() * 3,
        duration: Math.random() * 4 + 4,
      })),
    [],
  );
  const energyBeams = useMemo(
    () =>
      Array.from({ length: 5 }, () => ({
        offset: Math.random() * 50 - 25,
        delay: Math.random() * 2.5,
        duration: Math.random() * 1.5 + 2.5,
        skew: Math.random() * 8 - 4,
      })),
    [],
  );
  const uploadAnimationRef = useRef(null);
  const uploadTrackRef = useRef(null);
  const uploadDotRef = useRef(null);
  const uploadFolderRef = useRef(null);
  const uploadCloudRef = useRef(null);
  const statsContainerRef = useRef(null);
  const infoGridRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    let currentTimeoutId = null;

    // Function to fetch metrics with error handling
    const fetchMetrics = async () => {
      try {
        const data = await fetchJson("/metrics");
        if (!mounted) return;

        setMetrics({
          uploads: Number(data.uploads || 0),
          downloads: Number(data.downloads || 0),
          deleted: Number(data.deleted || 0),
          storage_bytes: Number(data.storage_bytes || 0),
        });
        setError(null); // Clear any previous error
        setLastSuccessfulUpdate(new Date());
      } catch (err) {
        if (!mounted) return;
        setError(err.message || "Failed to load metrics");
        console.warn("Metrics fetch failed:", err);
      }
      if (mounted) {
        setLoading(false);
      }
    };

    // Initial metrics fetch
    fetchMetrics();

    // Exponential backoff parameters
    let retryCount = 0;
    const maxRetryDelay = 60000; // Max 1 minute
    let currentDelay = 15000; // Start with 15 seconds

    // Function to start the polling with exponential backoff
    const startPolling = () => {
      if (currentTimeoutId) {
        clearTimeout(currentTimeoutId);
      }

      currentTimeoutId = setTimeout(async () => {
        try {
          const data = await fetchJson("/metrics");
          if (!mounted) return;

          setMetrics({
            uploads: Number(data.uploads || 0),
            downloads: Number(data.downloads || 0),
            deleted: Number(data.deleted || 0),
            storage_bytes: Number(data.storage_bytes || 0),
          });
          setError(null); // Clear any previous error
          setLastSuccessfulUpdate(new Date());
          retryCount = 0; // Reset retry count on success
          currentDelay = 15000; // Reset to initial delay on success
        } catch (err) {
          if (!mounted) return;
          setError(err.message || "Failed to load metrics");
          console.warn("Metrics fetch failed:", err);

          // Exponential backoff: double the delay after each failure, up to max
          retryCount++;
          currentDelay = Math.min(currentDelay * 2, maxRetryDelay);
        }

        // Schedule next poll
        if (mounted) {
          startPolling();
        }
      }, currentDelay);
    };

    // Function to stop the polling
    const stopPolling = () => {
      if (currentTimeoutId) {
        clearTimeout(currentTimeoutId);
        currentTimeoutId = null;
      }
    };

    // Visibility change handler - with exponential backoff logic
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // When tab becomes visible, reset the polling with initial delay
        currentDelay = 15000;
        retryCount = 0;
        startPolling();
      } else {
        stopPolling();
      }
    };

    // Start polling initially
    startPolling();

    // Add visibility change listener
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      mounted = false;
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  useEffect(() => {
    if (!uploadFolderRef.current || !uploadCloudRef.current) {
      return;
    }

    // Enhanced 3D animations using AnimeJS for the sophisticated visual elements
    const folderAnimation = anime({
      targets: uploadFolderRef.current,
      scale: [1, 1.08, 1],
      rotateY: [0, -5, 0],
      translateY: [0, -5, 0],
      duration: 3000,
      easing: 'easeInOutSine',
      loop: true,
      direction: 'alternate',
      delay: 0
    });

    const cloudAnimation = anime({
      targets: uploadCloudRef.current,
      scale: [1, 1.12, 1],
      rotateY: [0, 5, 0],
      translateY: [0, -7, 0],
      duration: 3500,
      easing: 'easeInOutSine',
      loop: true,
      direction: 'alternate',
      delay: 200
    });

    // Additional subtle floating effect for more 3D depth
    const subtleFloat = anime({
      targets: [uploadFolderRef.current, uploadCloudRef.current],
      translateY: [-3, 3, -3],
      duration: 4000,
      delay: anime.stagger(500),
      easing: 'easeInOutSine',
      loop: true,
      direction: 'alternate'
    });

    return () => {
      folderAnimation.pause();
      cloudAnimation.pause();
      subtleFloat.pause();
    };
  }, []);

  useEffect(() => {
    if (!statsContainerRef.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        statsContainerRef.current.querySelectorAll(".metric-card"),
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.8, ease: "power2.out", stagger: 0.1 },
      );
    }, statsContainerRef);
    return () => ctx.revert();
  }, [loading]);

  useEffect(() => {
    if (!infoGridRef.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        infoGridRef.current.querySelectorAll(".info-chip"),
        { opacity: 0, y: 12 },
        { opacity: 1, y: 0, duration: 0.7, ease: "power2.out", stagger: 0.08 },
      );
    }, infoGridRef);
    return () => ctx.revert();
  }, []);

  // Add interactive hover animations to highlight cards
  useEffect(() => {
    const highlightCards = document.querySelectorAll('.hero-grid article');
    const eventHandlers = [];

    highlightCards.forEach(card => {
      const handleMouseEnter = () => {
        gsap.to(card, {
          scale: 1.03,
          y: -5,
          duration: 0.3,
          ease: "power2.out",
          boxShadow: "0 25px 50px rgba(251, 113, 133, 0.25)",
        });
      };

      const handleMouseLeave = () => {
        gsap.to(card, {
          scale: 1,
          y: 0,
          duration: 0.3,
          ease: "power2.out",
          boxShadow: "0 45px 80px rgba(0, 0, 0, 0.65)",
        });
      };

      card.addEventListener('mouseenter', handleMouseEnter);
      card.addEventListener('mouseleave', handleMouseLeave);

      // Store the event handlers for cleanup
      eventHandlers.push({ card, handleMouseEnter, handleMouseLeave });
    });

    // Cleanup function to remove all event listeners
    return () => {
      eventHandlers.forEach(({ card, handleMouseEnter, handleMouseLeave }) => {
        card.removeEventListener('mouseenter', handleMouseEnter);
        card.removeEventListener('mouseleave', handleMouseLeave);
      });
    };
  }, []);

  useEffect(() => {
    const container = uploadAnimationRef.current;
    if (!container) return;

    const setTilt = (rotateYValue = 0, rotateXValue = 0) => {
      container.style.setProperty('--tilt-rotate-y', `${rotateYValue}deg`);
      container.style.setProperty('--tilt-rotate-x', `${rotateXValue}deg`);
      container.style.setProperty('--tilt-glow-x', `${rotateYValue * 1.2}px`);
      container.style.setProperty('--tilt-glow-y', `${rotateXValue * -1.2}px`);
    };

    const handlePointerMove = (event) => {
      const rect = container.getBoundingClientRect();
      const relativeX = (event.clientX - rect.left) / rect.width - 0.5;
      const relativeY = (event.clientY - rect.top) / rect.height - 0.5;
      const rotateYValue = relativeX * 12;
      const rotateXValue = relativeY * -10;
      setTilt(rotateYValue, rotateXValue);
    };

    const handlePointerLeave = () => setTilt(0, 0);

    setTilt(0, 0);
    container.addEventListener('pointermove', handlePointerMove);
    container.addEventListener('pointerleave', handlePointerLeave);

    return () => {
      container.removeEventListener('pointermove', handlePointerMove);
      container.removeEventListener('pointerleave', handlePointerLeave);
    };
  }, []);

  const stats = [
    { label: "Uploads", value: metrics.uploads, icon: "📤", formatter: formatNumber },
    { label: "Downloads", value: metrics.downloads, icon: "⚡", formatter: formatNumber },
    { label: "Cleanups", value: metrics.deleted, icon: "🧹", formatter: formatNumber },
    { label: "Storage", value: metrics.storage_bytes, icon: "🗄️", formatter: formatBytes },
  ];

  return (
    <div className="space-y-10">
      <section className="glass-card relative overflow-hidden p-8 md:p-12 grid gap-10 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="orbital-field" aria-hidden="true">
          <div className="orbital-ring orbital-ring--primary">
            <span className="orbital-satellite" />
          </div>
          <div className="orbital-ring orbital-ring--secondary">
            <span className="orbital-satellite" />
          </div>
        </div>
        <div className="sparkle">
          {sparklePositions.map((pos, index) => (
            <span key={index} style={pos} />
          ))}
        </div>
        <div className="space-y-6">
          <div className="tagline">Lightning file delivery</div>
          <h1 className="text-3xl md:text-5xl font-semibold leading-tight">
            Launch uploads that look premium, behave predictably, and scale effortlessly.
          </h1>
          <p className="text-slate-300 text-base md:text-lg">
            AlterBase CDN ingests binaries, mirrors them to MEGA, and cleans disks automatically. No dashboards, no cron
            hacking—just a API surface.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link className="button primary" to="/api-guide">
              Explore API Guide
            </Link>
            <a className="button secondary" href="https://github.com/lunaticsm/Image-Uploader-API" rel="noopener">
              View on GitHub
            </a>
          </div>
          <div className="info-grid" ref={infoGridRef}>
            {infoHighlights.map((item) => (
              <div key={item.text} className="info-chip text-sm text-slate-300">
                <span>{item.icon}</span>
                <span>{item.text}</span>
              </div>
            ))}
          </div>
        </div>
        {/* Feature highlights grid */}
        <div className="relative" ref={statsContainerRef}>
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-pink-500/5 rounded-3xl blur-xl -z-10"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Feature card 1: Upload Speed */}
            <div className="glass-card p-6 rounded-2xl border border-white/10 backdrop-blur-sm transform transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 group">
              <div className="flex items-start gap-4">
                <div className="text-4xl p-3 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-xl">🚀</div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">Lightning Fast Uploads</h3>
                  <p className="text-slate-300 text-sm">
                    Files are processed in real-time with minimal latency. Our optimized pipeline ensures your uploads reach users instantly.
                  </p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Speed</span>
                  <span>99.9%</span>
                </div>
                <div className="w-full bg-slate-700/50 rounded-full h-1.5 mt-1">
                  <div className="h-1.5 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400" style={{ width: '99.9%' }}></div>
                </div>
              </div>
            </div>

            {/* Feature card 2: Security */}
            <div className="glass-card p-6 rounded-2xl border border-white/10 backdrop-blur-sm transform transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 group">
              <div className="flex items-start gap-4">
                <div className="text-4xl p-3 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-xl">🔒</div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">Enterprise Security</h3>
                  <p className="text-slate-300 text-sm">
                    End-to-end encryption and secure file handling. Your files are protected with industry-standard security measures.
                  </p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Security</span>
                  <span>100%</span>
                </div>
                <div className="w-full bg-slate-700/50 rounded-full h-1.5 mt-1">
                  <div className="h-1.5 rounded-full bg-gradient-to-r from-green-500 to-emerald-400" style={{ width: '100%' }}></div>
                </div>
              </div>
            </div>

            {/* Feature card 3: Reliability */}
            <div className="glass-card p-6 rounded-2xl border border-white/10 backdrop-blur-sm transform transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 group">
              <div className="flex items-start gap-4">
                <div className="text-4xl p-3 bg-gradient-to-r from-rose-500/20 to-pink-500/20 rounded-xl">⚡</div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">High Availability</h3>
                  <p className="text-slate-300 text-sm">
                    99.99% uptime backed by redundant systems. Your files are always available with global CDN distribution.
                  </p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Reliability</span>
                  <span>99.99%</span>
                </div>
                <div className="w-full bg-slate-700/50 rounded-full h-1.5 mt-1">
                  <div className="h-1.5 rounded-full bg-gradient-to-r from-rose-500 to-pink-400" style={{ width: '99.99%' }}></div>
                </div>
              </div>
            </div>

            {/* Feature card 4: MEGA Integration */}
            <div className="glass-card p-6 rounded-2xl border border-white/10 backdrop-blur-sm transform transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 group">
              <div className="flex items-start gap-4">
                <div className="text-4xl p-3 bg-gradient-to-r from-yellow-500/20 to-amber-500/20 rounded-xl">☁️</div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">MEGA Backup</h3>
                  <p className="text-slate-300 text-sm">
                    Automatic mirroring to MEGA cloud storage. Your files have redundant backup with enterprise-grade reliability.
                  </p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Backups</span>
                  <span>Active</span>
                </div>
                <div className="w-full bg-slate-700/50 rounded-full h-1.5 mt-1">
                  <div className="h-1.5 rounded-full bg-gradient-to-r from-yellow-500 to-amber-400" style={{ width: '100%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* In-depth analytics dashboard */}
        <div className="w-full mt-10">
          <div className="text-center mb-6">
            <h3 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              Analytics Dashboard
            </h3>
            <p className="text-slate-400 mt-2">Advanced system metrics in real-time</p>
          </div>
          {loading ? (
            <div className="flex justify-center items-center py-12">
              <LoadingSpinner size="lg" message="Loading analytics dashboard..." />
            </div>
          ) : error ? (
            <div className="glass-card p-6 text-center">
              <div className="text-rose-400 font-semibold mb-2">⚠️ Metrics Unavailable</div>
              <p className="text-slate-300 text-sm mb-3">Unable to connect to metrics API. Data may be stale.</p>
              {lastSuccessfulUpdate && (
                <p className="text-xs text-slate-500">
                  Last successful update: {lastSuccessfulUpdate.toLocaleTimeString()}
                </p>
              )}
              <div className="mt-4">
                <button
                  className="button secondary text-xs"
                  onClick={() => {
                    // Manually trigger a refresh
                    const fetchMetrics = async () => {
                      try {
                        const data = await fetchJson("/metrics");
                        setMetrics({
                          uploads: Number(data.uploads || 0),
                          downloads: Number(data.downloads || 0),
                          deleted: Number(data.deleted || 0),
                          storage_bytes: Number(data.storage_bytes || 0),
                        });
                        setError(null);
                        setLastSuccessfulUpdate(new Date());
                      } catch (err) {
                        setError(err.message || "Failed to load metrics");
                      }
                    };
                    fetchMetrics();
                  }}
                >
                  Retry Connection
                </button>
              </div>
            </div>
          ) : (
            <>
              <AdvancedMetricVisualization
                data={stats}
              />
              <MetricBarChart
                data={stats}
              />
            </>
          )}
        </div>

        {/* Sophisticated 3D file transfer animation */}
        <div className="relative mt-12">
          {/* Animated background with particle effects */}
          <div className="absolute inset-0 rounded-3xl overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 via-purple-600/10 to-cyan-600/10"></div>
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(59,130,246,0.05)_0%,_transparent_70%)]"></div>
            <div
              className="absolute inset-0 opacity-30 mix-blend-screen animate-grid-drift"
              style={{
                backgroundImage:
                  'linear-gradient(120deg, rgba(6, 182, 212, 0.18) 1px, transparent 1px), linear-gradient(300deg, rgba(59, 130, 246, 0.12) 1px, transparent 1px)',
                backgroundSize: '60px 60px',
              }}
            ></div>
            <div className="absolute inset-0 pointer-events-none">
              {energyBeams.map((beam, index) => (
                <span
                  key={`beam-${index}`}
                  className="absolute left-[8%] right-[8%] h-px bg-gradient-to-r from-transparent via-cyan-200/80 to-transparent animate-energy-beam"
                  style={{
                    top: `calc(50% + ${beam.offset}px)`,
                    '--beam-skew': `${beam.skew}deg`,
                    animationDelay: `${beam.delay}s`,
                    animationDuration: `${beam.duration}s`,
                  }}
                ></span>
              ))}
            </div>

            {/* Floating particles */}
            <div className="absolute inset-0 overflow-hidden">
              {[...Array(20)].map((_, i) => (
                <div
                  key={i}
                  className="absolute rounded-full bg-gradient-to-r from-cyan-400/20 to-blue-500/20 animate-ping"
                  style={{
                    width: `${Math.random() * 6 + 2}px`,
                    height: `${Math.random() * 6 + 2}px`,
                    left: `${Math.random() * 100}%`,
                    top: `${Math.random() * 100}%`,
                    animationDuration: `${Math.random() * 4 + 2}s`,
                    animationDelay: `${Math.random() * 2}s`
                  }}
                ></div>
              ))}
            </div>
            <div className="absolute inset-0 pointer-events-none">
              {floatingNodes.map((node, index) => (
                <div
                  key={`node-${index}`}
                  className="absolute rounded-full bg-gradient-to-r from-cyan-400/20 to-blue-500/30 shadow-lg shadow-cyan-500/30 animate-node-pulse"
                  style={{
                    top: node.top,
                    left: node.left,
                    width: `${node.size}px`,
                    height: `${node.size}px`,
                    animationDelay: `${node.delay}s`,
                    animationDuration: `${node.duration}s`,
                  }}
                >
                  <div className="absolute inset-0 rounded-full border border-cyan-400/20 animate-node-orbit"></div>
                </div>
              ))}
            </div>
          </div>

          {/* Dynamic animated border */}
          <div className="absolute inset-0 rounded-3xl">
            <div className="w-full h-full rounded-3xl bg-[length:300%_300%] bg-[linear-gradient(45deg,_#3b82f6,_#8b5cf6,_#06b6d4,_#3b82f6)] animate-border-move"></div>
          </div>

          {/* 3D perspective container */}
          <div
            className="relative z-10 px-6 py-10 md:px-12 md:py-14 transform-style-3d group"
            style={{
              perspective: '1000px',
              '--tilt-rotate-x': '0deg',
              '--tilt-rotate-y': '0deg',
              '--tilt-glow-x': '0px',
              '--tilt-glow-y': '0px',
            }}
            ref={uploadAnimationRef}
          >
            <div
              className="pointer-events-none absolute inset-6 rounded-[36px] bg-gradient-to-r from-blue-500/20 via-transparent to-cyan-500/20 blur-3xl opacity-70 transition-transform duration-700 ease-out"
              style={{
                transform: 'translate(var(--tilt-glow-x, 0px), var(--tilt-glow-y, 0px))',
              }}
            ></div>
            <div
              className="pointer-events-none absolute inset-2 rounded-[36px] border border-cyan-400/30 opacity-0 transition-all duration-500 group-hover:opacity-80"
              style={{
                transform: 'translate(calc(var(--tilt-glow-x, 0px) / 2), calc(var(--tilt-glow-y, 0px) / 2))',
              }}
            ></div>
            <div
              className="transfer-panel transform-gpu transition-transform duration-500 ease-out"
              style={{
                transform: 'rotateX(var(--tilt-rotate-x, 0deg)) rotateY(var(--tilt-rotate-y, 0deg))',
              }}
            >
              <div className="transfer-panel__header">
                <div className="transfer-chip">Live Transfer</div>
                <span className="transfer-subtitle">Quantum-grade encryption</span>
                <div className="transfer-checks">
                  {[0, 1, 2].map((state) => (
                    <span key={`check-${state}`} className="transfer-check">✓</span>
                  ))}
                </div>
              </div>

              <div className="transfer-panel__body">
                {/* Source tower */}
                <div ref={uploadFolderRef} className="transfer-tower transfer-tower--source">
                  <div className="transfer-tower__icon">💻</div>
                  <div className="transfer-tower__content">
                    <h4>Source Device</h4>
                    <p>Files staged &amp; encrypted</p>
                  </div>
                  <div className="transfer-tower__stack">
                    {[...Array(4)].map((_, idx) => (
                      <span key={idx} style={{ '--stack-delay': `${idx * 0.2}s` }}>📄</span>
                    ))}
                  </div>
                </div>

                {/* Center animation */}
                <div className="transfer-panel__center">
                  <div className="transfer-path transfer-path--compressed">
                    <div className="transfer-path__glow"></div>
                    <div className="transfer-path__pulse"></div>
                    <div className="transfer-path__grid">
                      {Array.from({ length: 12 }).map((_, segmentIndex) => (
                        <span key={`segment-${segmentIndex}`} className="transfer-path__segment"></span>
                      ))}
                    </div>
                    <div className="transfer-path__particles">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <div
                          key={i}
                          className="transfer-packet"
                          style={{
                            animationDelay: `${i * 0.4}s`,
                            animationDuration: `${3 + i * 0.25}s`,
                          }}
                        >
                          <div className="transfer-packet__core"></div>
                        </div>
                      ))}
                    </div>
                    <div className="transfer-path__carrier">
                      <span className="transfer-path__file">📄</span>
                    </div>
                  </div>
                  <div className="transfer-statuses">
                    {[
                      { label: "125 Mbps", gradient: "from-cyan-400 to-sky-500" },
                      { label: "Secure", gradient: "from-emerald-400 to-teal-400" },
                      { label: "Uploading…", gradient: "from-indigo-400 to-purple-500" },
                    ].map((pill) => (
                      <div key={pill.label} className={`transfer-status bg-gradient-to-r ${pill.gradient}`}>
                        <span>{pill.label}</span>
                      </div>
                    ))}
                  </div>
                  <div className="transfer-progress">4 files left • integrity checks running</div>
                </div>

                {/* Destination tower */}
                <div ref={uploadCloudRef} className="transfer-tower transfer-tower--destination">
                  <div className="transfer-tower__icon">☁️</div>
                  <div className="transfer-tower__content">
                    <h4>Cloud Storage</h4>
                    <p>Synced across regions</p>
                  </div>
                  <div className="transfer-tower__badges">
                    {["AES-256", "Redundant", "Checksummed"].map((badge, idx) => (
                      <span key={badge} style={{ animationDelay: `${idx * 0.15}s` }}>
                        {badge}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="transfer-panel__footer">
                <p className="transfer-panel__headline">
                  Securely transferring your files with end-to-end encryption
                </p>
                <p className="transfer-panel__subhead">
                  From your device to cloud storage in real-time with verifiable integrity checks.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="glass-card p-8 space-y-6">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="glow-pill">
            <span>🛰️</span>
            <span>Workflow in orbit</span>
          </div>
          <p className="text-sm text-slate-400">The calm pipeline for aggressive teams.</p>
        </div>
        <ol className="workflow">
          {workflow.map((item, index) => (
            <li
              key={item.step}
              className="workflow-item"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <span>{item.step}</span>
              <div>
                <strong>{item.title}</strong>
                <p>{item.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="hero-grid">
        {highlights.map((feature, index) => (
          <article
            key={feature.title}
            className="glass-card p-5 space-y-3 animate-fadeInSlideUp"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <h3 className="text-xl font-semibold">
              {feature.emoji} {feature.title}
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed">{feature.text}</p>
          </article>
        ))}
      </section>

      <section className="glass-card p-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="tagline">Ready to deploy?</p>
          <h2 className="text-2xl font-semibold mt-2">Bootstrap your own micro-CDN in minutes.</h2>
          <p className="text-slate-400 text-sm mt-2">
            Clone the repo, copy `.env-sample`, wire MEGA credentials, and run `docker compose up`. No dashboards—just API.
          </p>
        </div>
        <div className="flex gap-3 flex-wrap">
          <a className="button primary" href="https://github.com/lunaticsm/Image-Uploader-API" rel="noopener">
            View on GitHub
          </a>
          <Link className="button secondary" to="/api-guide">
            API reference
          </Link>
        </div>
      </section>
    </div>
  );
}

export default HomePage;

import { Link } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import { gsap } from "gsap";
import anime from "animejs";
import AnimatedNumber from "../components/AnimatedNumber";
import { fetchJson } from "../lib/api";
import { formatBytes, formatNumber } from "../lib/formatters";

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
  const sparklePositions = useMemo(
    () => sparkles.map(() => ({ top: `${Math.random() * 100}%`, left: `${Math.random() * 100}%` })),
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
    fetchJson("/metrics")
      .then((data) => {
        if (mounted) {
          setMetrics({
            uploads: Number(data.uploads || 0),
            downloads: Number(data.downloads || 0),
            deleted: Number(data.deleted || 0),
            storage_bytes: Number(data.storage_bytes || 0),
          });
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
    const interval = setInterval(() => {
      fetchJson("/metrics").then((data) => {
        if (!mounted) return;
        setMetrics({
          uploads: Number(data.uploads || 0),
          downloads: Number(data.downloads || 0),
          deleted: Number(data.deleted || 0),
          storage_bytes: Number(data.storage_bytes || 0),
        });
      });
    }, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!uploadTrackRef.current || !uploadDotRef.current || !uploadFolderRef.current || !uploadCloudRef.current) {
      return;
    }

    const buildTimeline = () => {
      const trackWidth = uploadTrackRef.current.clientWidth;
      const dotWidth = uploadDotRef.current.clientWidth;
      const travel = Math.max(trackWidth - dotWidth, 0);

      const timeline = anime.timeline({ loop: true, autoplay: true });

      timeline
        .add({
          targets: uploadDotRef.current,
          translateX: travel,
          opacity: [{ value: 0.25, duration: 150 }, { value: 1, duration: 250 }],
          easing: "easeInOutCubic",
          duration: 2000,
        })
        .add(
          {
            targets: uploadCloudRef.current,
            scale: [1, 1.14],
            easing: "easeOutBack",
            duration: 350,
            direction: "alternate",
            loop: 1,
          },
          "-=400",
        )
        .add({
          targets: uploadDotRef.current,
          opacity: [1, 0],
          duration: 200,
          easing: "linear",
        })
        .add({
          targets: uploadDotRef.current,
          translateX: 0,
          opacity: 0,
          duration: 1,
        });

      anime({
        targets: [uploadFolderRef.current, uploadCloudRef.current],
        translateY: [-4, 4],
        direction: "alternate",
        easing: "easeInOutSine",
        duration: 1500,
        delay: anime.stagger(150),
        loop: true,
      });

      return timeline;
    };

    let timeline = buildTimeline();

    const handleResize = () => {
      timeline.pause();
      anime.remove(uploadDotRef.current);
      timeline = buildTimeline();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      timeline.pause();
      anime.remove(uploadDotRef.current);
      anime.remove([uploadFolderRef.current, uploadCloudRef.current]);
      window.removeEventListener("resize", handleResize);
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
        <div className="grid gap-4 sm:grid-cols-2" ref={statsContainerRef}>
          {stats.map((metric) => (
            <div key={metric.label} className="metric-card">
              <span className="label">
                {metric.icon} {metric.label}
              </span>
              <AnimatedNumber value={loading ? 0 : metric.value} format={metric.formatter} />
            </div>
          ))}
        </div>

        <div className="upload-animation mt-6" ref={uploadAnimationRef}>
          <div className="upload-row">
            <div className="upload-icon upload-icon--source" ref={uploadFolderRef}>
              📁
            </div>
            <div className="upload-track" ref={uploadTrackRef}>
              <div className="upload-dot" ref={uploadDotRef} />
            </div>
            <div className="upload-icon upload-icon--cloud" ref={uploadCloudRef}>
              ☁️
            </div>
          </div>
          <p className="upload-caption">Files stream to disk, mirror to MEGA, and soar to your users.</p>
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
          {workflow.map((item) => (
            <li key={item.step}>
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
        {highlights.map((feature) => (
          <article key={feature.title} className="glass-card p-5 space-y-3">
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

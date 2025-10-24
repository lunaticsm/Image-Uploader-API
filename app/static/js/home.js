const metricCards = document.querySelectorAll(".metric");

function formatNumber(value, format) {
  if (Number.isNaN(value)) {
    value = 0;
  }
  if (format === "bytes") {
    if (value <= 0) {
      return "0 B";
    }
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = value;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex += 1;
    }
    const decimals = unitIndex === 0 ? 0 : size < 10 ? 2 : 1;
    return (
      size.toFixed(decimals).replace(/\.0+$/, "") + " " + units[unitIndex]
    );
  }
  return value.toLocaleString("en-US");
}

function scramble(el, finalValue, format) {
  const duration = 900;
  if (!Number.isFinite(finalValue)) {
    el.textContent = formatNumber(0, format);
    return;
  }
  if (finalValue === 0) {
    el.textContent = formatNumber(0, format);
    return;
  }
  const start = performance.now();
  const cap = Math.max(finalValue, 20);

  function update(now) {
    const progress = Math.min((now - start) / duration, 1);
    if (progress < 1) {
      const randomCap = format === "bytes" ? Math.max(finalValue, 1) : cap;
      const randomValue = Math.floor(Math.random() * (randomCap + 1));
      el.textContent = formatNumber(randomValue, format);
      requestAnimationFrame(update);
    } else {
      el.textContent = formatNumber(finalValue, format);
    }
  }

  requestAnimationFrame(update);
}

function applyMetrics(data) {
  metricCards.forEach(function (card) {
    const key = card.getAttribute("data-key");
    const nextValue = Number(data[key] || 0);
    const current = Number(card.getAttribute("data-current") || "-1");
    const format = card.getAttribute("data-format") || "number";
    if (current === nextValue) {
      return;
    }
    card.setAttribute("data-current", String(nextValue));
    const valueEl = card.querySelector(".value");
    scramble(valueEl, nextValue, format);
  });
}

const initialMetrics = {};
metricCards.forEach(function (card) {
  const key = card.getAttribute("data-key");
  initialMetrics[key] = Number(card.getAttribute("data-value") || "0");
});
applyMetrics(initialMetrics);

async function refreshMetrics() {
  try {
    const response = await fetch("/metrics", { cache: "no-store" });
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    applyMetrics(payload);
  } catch (err) {
    console.error("metrics refresh failed", err);
  }
}

setTimeout(refreshMetrics, 250);
setInterval(refreshMetrics, 15000);

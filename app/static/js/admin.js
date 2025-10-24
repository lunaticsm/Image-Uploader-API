(function () {
  const run = () => {
    const flash = document.querySelector(".flash[data-flash-reason='auth']");
    if (!flash) {
      return;
    }
    const message = flash.textContent ? flash.textContent.trim() : "";
    if (!message) {
      return;
    }
    if (flash.dataset.popupShown === "1") {
      return;
    }
    flash.dataset.popupShown = "1";
    window.alert(message);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run, { once: true });
  } else {
    run();
  }
})();

// Aurelian Pulse - progressive enhancement only. No external calls.
// The site is fully functional without JS; this just adds life.
(function () {
  "use strict";

  // "/" focuses search, like the real thing.
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" &&
        document.activeElement.tagName !== "TEXTAREA") {
      var box = document.querySelector(".searchbox input");
      if (box) { e.preventDefault(); box.focus(); }
    }
  });

  // Like / retweet toggles with a little pop.
  function wireToggle(sel, cls) {
    document.querySelectorAll(sel).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var span = btn.querySelector("span[data-n]");
        var n = parseInt(span.getAttribute("data-n"), 10) || 0;
        var on = btn.classList.toggle(cls);
        span.textContent = on ? n + 1 : n;
        span.classList.remove("pop"); void span.offsetWidth; span.classList.add("pop");
      });
    });
  }
  wireToggle("[data-like]", "on");
  wireToggle("[data-rt]", "on");

  // Follow buttons toggle.
  document.querySelectorAll("[data-follow]").forEach(function (b) {
    b.addEventListener("click", function () {
      var on = !b.classList.toggle("off");
      b.textContent = on ? "Following" : "Follow";
    });
  });

  // Compose focus from the sidebar "Post" button.
  document.querySelectorAll("[data-compose-focus]").forEach(function (b) {
    b.addEventListener("click", function () {
      var ta = document.querySelector("[data-compose]");
      if (ta) ta.focus();
    });
  });

  // Relative timestamps ("2d", "4h"), keeping the full date as a tooltip.
  function rel(tsStr) {
    var t = new Date(tsStr.replace(" ", "T"));
    if (isNaN(t)) return null;
    var s = Math.floor((Date.now() - t.getTime()) / 1000);
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m";
    if (s < 86400) return Math.floor(s / 3600) + "h";
    if (s < 2592000) return Math.floor(s / 86400) + "d";
    return Math.floor(s / 2592000) + "mo";
  }
  document.querySelectorAll("[data-ts]").forEach(function (el) {
    var r = rel(el.getAttribute("data-ts"));
    if (r) { el.title = el.getAttribute("data-ts"); el.textContent = "· " + r; }
  });
})();

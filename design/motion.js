/* App hub motion, from the prototype's script: count-up, the calculator roll, and reveal-on-scroll.
   views/ui.py loads this once per page with st.html(unsafe_allow_javascript=True). Nothing in it reads user input.
   Every element is already in its final state in the HTML, so if this never runs the page is complete, only still.
     data-count="612" data-delay="800"         counts up from 0 (hero, first visit only)
     data-roll-from="605" data-roll-to="1008"  rolls from the previous estimate to the new one
     data-reveal="home-steps"                  adds .in the first time it scrolls into view, once per session */
(function () {
  if (window.__hubMotion) return;
  window.__hubMotion = true;
  document.documentElement.classList.add("hub-js");

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var fmt = function (n) { return Math.round(n).toLocaleString("en-US"); };

  function tween(node, from, to, duration, delay) {
    if (reduced.matches || from === to || !isFinite(from) || !isFinite(to)) { node.textContent = fmt(to); return; }
    node.textContent = fmt(from);
    var start = null;
    function tick(now) {
      if (!node.isConnected) return;
      if (start === null) start = now + delay;
      var p = Math.min(1, Math.max(0, (now - start) / duration));
      node.textContent = fmt(from + (to - from) * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  var seen = {};
  var io = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      seen[e.target.getAttribute("data-reveal")] = true;
      io.unobserve(e.target);
    });
  }, { threshold: 0.35 }) : null;

  function scan() {
    document.querySelectorAll(".hub [data-count]:not([data-hub-done])").forEach(function (n) {
      n.setAttribute("data-hub-done", "");
      tween(n, 0, Number(n.getAttribute("data-count")), 1400, Number(n.getAttribute("data-delay") || 0));
    });
    document.querySelectorAll(".hub [data-roll-to]:not([data-hub-done])").forEach(function (n) {
      n.setAttribute("data-hub-done", "");
      tween(n, Number(n.getAttribute("data-roll-from")), Number(n.getAttribute("data-roll-to")), 450, 0);
    });
    document.querySelectorAll(".hub [data-reveal]:not([data-hub-done])").forEach(function (n) {
      n.setAttribute("data-hub-done", "");
      if (!io || reduced.matches || seen[n.getAttribute("data-reveal")]) { n.classList.add("in", "instant"); return; }
      io.observe(n);
    });
  }

  // Streamlit adds and replaces elements on every rerun; look again before the next paint.
  var queued = false;
  new MutationObserver(function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; scan(); });
  }).observe(document.body, { childList: true, subtree: true });
  scan();
})();

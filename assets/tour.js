/* Spotlight "how to use this dashboard" walkthrough engine.
 *
 * Pure client-side. The step DATA is defined in Python (src/components/tour.py)
 * and handed in via window.WCTour.setSteps(...) from a Dash clientside callback;
 * start() is called from the light-bulb button's clientside callback.
 *
 * For each step the engine:
 *   1. makes sure the app is in the mode the step needs (clicks #mode-toggle,
 *      remembering the original mode so it can restore it on exit),
 *   2. finds the target element, inflates a "spotlight" cut-out over it (a div
 *      whose huge box-shadow dims everything else), and
 *   3. positions the step card on whichever side has the most room.
 *
 * No target (or a hidden one) => a centred card over a full dim.
 */
(function () {
  "use strict";

  var PAD = 8;          // spotlight padding around the target (px)
  var GAP = 14;         // gap between spotlight and card (px)
  var MARGIN = 12;      // min distance from any viewport edge (px)
  var MODE_WAIT = 480;  // ms to let the layout re-render after a mode flip

  function $(sel) { return document.querySelector(sel); }

  // The mode switch is checked == Team view, unchecked == Time view.
  function currentMode() {
    var t = document.getElementById("mode-toggle");
    return t && t.checked ? "team" : "time";
  }

  function setMode(mode, done) {
    if (!mode || currentMode() === mode) { done(0); return; }
    var t = document.getElementById("mode-toggle");
    if (t) { t.click(); done(MODE_WAIT); return; }
    done(0);
  }

  // Resolve a step's target to a measurable element. Switch inputs are visually
  // hidden offscreen, so spotlight their visible root instead.
  function resolveTarget(sel) {
    if (!sel) return null;
    var el = $(sel);
    if (!el) return null;
    if (el.tagName === "INPUT") {
      el = el.closest(".mantine-Switch-root") || el.parentElement || el;
    }
    return el;
  }

  function isVisible(el) {
    if (!el) return false;
    var r = el.getBoundingClientRect();
    return r.width > 1 && r.height > 1;
  }

  var WCTour = {
    steps: [],
    i: -1,
    originalMode: null,
    active: false,
    _targetEl: null,

    setSteps: function (steps) {
      if (Array.isArray(steps)) this.steps = steps;
    },

    // Light / un-light the trigger bulb so it reads as a toggle.
    _setBulb: function (on) {
      var bulb = document.getElementById("tour-control");
      if (bulb) bulb.classList.toggle("map-control--active", !!on);
    },

    // First-load nudge: pulse the bulb to draw the eye, until the user has
    // opened the tour at least once (remembered across reloads).
    nudge: function (tries) {
      var seen;
      try { seen = localStorage.getItem("wc_tour_seen"); } catch (e) { seen = null; }
      if (seen) return;
      var bulb = document.getElementById("tour-control");
      if (bulb) { bulb.classList.add("map-control--attention"); return; }
      // The control may not have mounted yet; retry a few times.
      if ((tries || 0) < 10) {
        var self = this;
        setTimeout(function () { self.nudge((tries || 0) + 1); }, 300);
      }
    },

    _clearNudge: function () {
      try { localStorage.setItem("wc_tour_seen", "1"); } catch (e) {}
      var bulb = document.getElementById("tour-control");
      if (bulb) bulb.classList.remove("map-control--attention");
    },

    toggle: function () {
      if (this.active) this.stop(); else this.start();
    },

    start: function () {
      if (!this.steps.length) return;
      this.active = true;
      this._clearNudge();
      this._setBulb(true);
      // Lift the controls above the dim so the bulb stays clickable (toggle off).
      var controls = document.getElementById("map-controls-overlay");
      if (controls) controls.classList.add("tour-lift");
      this.originalMode = currentMode();
      // Capture phase so a focused control can't swallow Esc/arrows first.
      document.addEventListener("keydown", this._onKey, true);
      this.goto(0);
    },

    stop: function () {
      var self = this;
      this.active = false;
      this._setBulb(false);
      var controls = document.getElementById("map-controls-overlay");
      if (controls) controls.classList.remove("tour-lift");
      if (this._targetEl) {
        this._targetEl.classList.remove("tour-target-active");
        this._targetEl = null;
      }
      document.removeEventListener("keydown", this._onKey, true);
      var overlay = $("#tour-overlay");
      // Restore the mode the user was in before the tour started.
      setMode(this.originalMode, function () {
        if (overlay) overlay.style.display = "none";
      });
      if (overlay) overlay.style.display = "none";
      this.i = -1;
    },

    next: function () {
      if (this.i >= this.steps.length - 1) { this.stop(); return; }
      this.goto(this.i + 1);
    },

    prev: function () {
      if (this.i > 0) this.goto(this.i - 1);
    },

    goto: function (idx) {
      var self = this;
      this.i = idx;
      var step = this.steps[idx];
      if (!step) { this.stop(); return; }
      var overlay = $("#tour-overlay");
      if (overlay) overlay.style.display = "block";
      this._fillCard(step, idx);
      // Switch mode if needed, then place the spotlight (after a re-render beat).
      setMode(step.mode, function (wait) {
        if (wait) {
          setTimeout(function () { self._place(step); }, wait);
        } else {
          self._place(step);
        }
      });
    },

    _fillCard: function (step, idx) {
      var title = $("#tour-card-title");
      var body = $("#tour-card-body");
      var prog = $("#tour-card-progress");
      if (title) title.textContent = step.title || "";
      if (body) body.textContent = step.body || "";
      if (prog) {
        var dots = "";
        for (var k = 0; k < this.steps.length; k++) {
          dots += '<span class="tour-dot' +
            (k === idx ? " tour-dot--on" : "") + '"></span>';
        }
        prog.innerHTML = dots;
      }
      var back = $("#tour-back");
      if (back) back.disabled = idx === 0;
      var next = $("#tour-next");
      if (next) {
        // DMC renders the label inside a span; set textContent on the button.
        var lbl = next.querySelector(".mantine-Button-label") || next;
        lbl.textContent = idx >= this.steps.length - 1 ? "Done" : "Next";
      }
    },

    _place: function (step) {
      var overlay = $("#tour-overlay");
      var spot = $("#tour-spotlight");
      var card = $("#tour-card");
      if (!overlay || !spot || !card) return;
      var el = resolveTarget(step.target);

      // Keep the currently-spotlighted control bright while its siblings fade.
      if (this._targetEl) this._targetEl.classList.remove("tour-target-active");
      this._targetEl = el;
      if (el) el.classList.add("tour-target-active");

      if (!el || !isVisible(el)) {
        // No anchor: full dim, centred card.
        overlay.classList.add("tour-overlay--full");
        spot.style.display = "none";
        card.style.left = "50%";
        card.style.top = "50%";
        card.style.transform = "translate(-50%, -50%)";
        return;
      }

      overlay.classList.remove("tour-overlay--full");
      spot.style.display = "block";
      card.style.transform = "none";

      var r = el.getBoundingClientRect();
      var sx = Math.max(r.left - PAD, 0);
      var sy = Math.max(r.top - PAD, 0);
      var sw = Math.min(r.width + PAD * 2, window.innerWidth - sx);
      var sh = Math.min(r.height + PAD * 2, window.innerHeight - sy);
      spot.style.left = sx + "px";
      spot.style.top = sy + "px";
      spot.style.width = sw + "px";
      spot.style.height = sh + "px";

      this._placeCard(card, sx, sy, sw, sh);
    },

    // Put the card on whichever side of the spotlight has the most room, then
    // clamp it inside the viewport. On narrow screens, dock it to the bottom.
    _placeCard: function (card, sx, sy, sw, sh) {
      var cw = card.offsetWidth || 300;
      var ch = card.offsetHeight || 160;
      var vw = window.innerWidth;
      var vh = window.innerHeight;

      if (vw < 640) {
        var left = Math.max(MARGIN, (vw - cw) / 2);
        // Below the spotlight if it fits, otherwise above it.
        var top = sy + sh + GAP;
        if (top + ch > vh - MARGIN) top = sy - GAP - ch;
        if (top < MARGIN) top = vh - ch - MARGIN;
        // Final guard: never let the card spill past either edge.
        top = Math.min(Math.max(top, MARGIN), vh - ch - MARGIN);
        card.style.left = left + "px";
        card.style.top = top + "px";
        return;
      }

      var space = {
        bottom: vh - (sy + sh),
        top: sy,
        right: vw - (sx + sw),
        left: sx,
      };
      var side = "bottom", best = -Infinity;
      for (var k in space) {
        if (space[k] > best) { best = space[k]; side = k; }
      }

      var cl, ct;
      if (side === "bottom" || side === "top") {
        cl = sx + sw / 2 - cw / 2;
        ct = side === "bottom" ? sy + sh + GAP : sy - GAP - ch;
      } else {
        ct = sy + sh / 2 - ch / 2;
        cl = side === "right" ? sx + sw + GAP : sx - GAP - cw;
      }
      cl = Math.min(Math.max(cl, MARGIN), vw - cw - MARGIN);
      ct = Math.min(Math.max(ct, MARGIN), vh - ch - MARGIN);
      card.style.left = cl + "px";
      card.style.top = ct + "px";
    },

    _onKey: function (e) {
      if (e.key === "Escape") { WCTour.stop(); }
      else if (e.key === "ArrowRight") { WCTour.next(); }
      else if (e.key === "ArrowLeft") { WCTour.prev(); }
    },
  };

  // Delegated controls — robust to when the card mounts/re-renders.
  document.addEventListener("click", function (e) {
    if (!WCTour.active) return;
    if (e.target.closest("#tour-next")) { e.preventDefault(); WCTour.next(); }
    else if (e.target.closest("#tour-back")) { e.preventDefault(); WCTour.prev(); }
    else if (e.target.closest("#tour-skip")) { e.preventDefault(); WCTour.stop(); }
  });

  // Keep the spotlight glued to its target through resizes/scroll.
  window.addEventListener("resize", function () {
    if (WCTour.active && WCTour.i >= 0) WCTour._place(WCTour.steps[WCTour.i]);
  });

  window.WCTour = WCTour;
})();

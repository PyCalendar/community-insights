/* Light, dark or automatic (as the system) page, and the charts with it. The
   choice is kept in the cookie "theme" so the server renders the page and its
   charts in it at once. Loaded in <head> to avoid a flash of the wrong theme. */
(function () {
  "use strict";

  var CHOICES = ["auto", "light", "dark"];
  /* The icon of the button of the switch for each choice. */
  var ICONS = { auto: "\u25D0", light: "\u2600", dark: "\u263E" };

  function readChoice(cookies) {
    var match = /(?:^|;\s*)theme=([a-z]+)/.exec(cookies || "");
    return match && CHOICES.indexOf(match[1]) >= 0 ? match[1] : "auto";
  }

  /* "light" or "dark" for a choice and whether the system prefers dark. */
  function resolve(choice, prefersDark) {
    if (choice === "light" || choice === "dark") return choice;
    return prefersDark ? "dark" : "light";
  }

  /* The address of a chart in a theme; other parameters stay. */
  function chartUrl(base, theme) {
    var url = base.replace(/([?&])theme=[a-z]*(&|$)/, function (all, before, after) {
      return after ? before : "";
    });
    return url + (url.indexOf("?") >= 0 ? "&" : "?") + "theme=" + theme;
  }

  function apply(doc, choice, prefersDark) {
    var theme = resolve(choice, prefersDark);
    var root = doc.documentElement;
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-bs-theme", theme);
    root.setAttribute("data-theme-choice", choice);
    var charts = doc.querySelectorAll ? doc.querySelectorAll("img[data-chart-src]") : [];
    Array.prototype.forEach.call(charts, function (img) {
      var wanted = chartUrl(img.getAttribute("data-chart-src"), theme);
      if (img.getAttribute("src") !== wanted) img.setAttribute("src", wanted);
    });
    var icons = doc.querySelectorAll ? doc.querySelectorAll("[data-theme-icon]") : [];
    Array.prototype.forEach.call(icons, function (icon) {
      icon.textContent = ICONS[choice] || ICONS.auto;
    });
    var buttons = doc.querySelectorAll ? doc.querySelectorAll("[data-theme-set]") : [];
    Array.prototype.forEach.call(buttons, function (button) {
      var active = button.getAttribute("data-theme-set") === choice;
      button.setAttribute("aria-pressed", active ? "true" : "false");
      if (button.classList) button.classList.toggle("active", active);
    });
    return theme;
  }

  function setup(win) {
    var doc = win.document;
    var media = win.matchMedia ? win.matchMedia("(prefers-color-scheme: dark)") : null;
    function prefersDark() { return !!(media && media.matches); }
    function choose(choice) {
      doc.cookie = "theme=" + choice + ";path=/;max-age=31536000;samesite=lax";
      return apply(doc, choice, prefersDark());
    }
    apply(doc, readChoice(doc.cookie), prefersDark());
    if (media && media.addEventListener) {
      media.addEventListener("change", function () {
        apply(doc, readChoice(doc.cookie), prefersDark());
      });
    }
    doc.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("[data-theme-set]");
      if (button) choose(button.getAttribute("data-theme-set"));
    });
    // the charts are below this script: switch them when the page is there
    doc.addEventListener("DOMContentLoaded", function () {
      apply(doc, readChoice(doc.cookie), prefersDark());
    });
    return choose;
  }

  var api = { ICONS: ICONS, readChoice: readChoice, resolve: resolve, chartUrl: chartUrl, apply: apply, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    setup(window);
  }
})();

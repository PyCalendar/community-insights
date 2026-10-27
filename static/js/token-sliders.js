/* The two sliders of a token: the maximum points per hour the site uses, and
   the share of that maximum given to everybody else. The share is a part of
   the maximum, so moving the maximum moves the shared points with it. The
   model AccessToken computes the same numbers. */
(function () {
  "use strict";

  /* A text in the language of the page (Django's JavaScript catalog); in
     node, the English text. `_` is the name xgettext looks for. */
  function _(text) {
    return typeof gettext === "function" ? gettext(text) : text;
  }

  /* A translated text with %(name)s replaced by the values. */
  function t(text, values) {
    return text.replace(/%\((\w+)\)s/g, function (all, name) { return String(values[name]); });
  }

  function clamp(percent) {
    var value = Math.round(Number(percent));
    if (!isFinite(value)) return 0;
    return Math.max(0, Math.min(100, value));
  }

  /* The points for a limit per hour (5000 at GitHub) and the two percentages. */
  function points(limit, maxPercent, sharedPercent) {
    var max = Math.round(limit * clamp(maxPercent) / 100);
    var shared = Math.round(max * clamp(sharedPercent) / 100);
    return { max: max, shared: shared, reserve: limit - max, own: max - shared };
  }

  function describe(limit, maxPercent, sharedPercent) {
    var p = points(limit, maxPercent, sharedPercent);
    return {
      max: t(_("%(max)s of %(limit)s points per hour, stopping when %(reserve)s are left"),
        { max: p.max, limit: limit, reserve: p.reserve }),
      shared: t(_("%(shared)s of %(max)s points per hour for others on this site"),
        { shared: p.shared, max: p.max }),
      points: p,
    };
  }

  function setup(root) {
    var limit = Number(root.getAttribute("data-limit")) || 5000;
    var max = root.querySelector("[data-slider=max]");
    var shared = root.querySelector("[data-slider=shared]");
    function update() {
      var text = describe(limit, max.value, shared.value);
      root.querySelector("[data-slider-text=max]").textContent = text.max;
      root.querySelector("[data-slider-text=shared]").textContent = text.shared;
      return text;
    }
    max.addEventListener("input", update);
    shared.addEventListener("input", update);
    return update();
  }

  var api = { clamp: clamp, points: points, describe: describe, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-token-sliders]").forEach(setup);
  }
})();

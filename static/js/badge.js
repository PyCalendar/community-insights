/* The badge builder of the overview: an element with data-badge-url and the
   fields data-badge="kind|percentile|class|model|label" and an <img data-badge="preview">.
   The code to share the badge is filled by static/js/share.js (window.Share). */
(function () {
  "use strict";

  /* The URL of a badge. The percentile is limited to 0-100. */
  function badgeUrl(base, kind, percentile, className, label, model) {
    var p = Number(percentile);
    if (!isFinite(p)) p = 50;
    p = Math.min(100, Math.max(0, p));
    /* the base can carry the classes of the page already: ?classes=... */
    var query = (base.indexOf("?") >= 0 ? "&" : "?") + "kind=" + (kind === "issue" ? "issue" : "pr") + "&percentile=" + p;
    if (className) query += "&class=" + encodeURIComponent(className);
    if (model && model !== "measured") query += "&model=" + encodeURIComponent(model);
    var text = String(label || "").trim();
    if (text) query += "&label=" + encodeURIComponent(text);
    return base + query;
  }

  /* The text of the image for people who cannot see it. */
  function altText(kind, label) {
    var text = String(label || "").trim();
    if (text) return text;
    return kind === "issue" ? "issue response time" : "pull request response time";
  }

  function setup(root, share) {
    var base = root.getAttribute("data-badge-url");
    function part(name) {
      return root.querySelector('[data-badge="' + name + '"]');
    }
    var kind = part("kind"), percentile = part("percentile"), className = part("class"), label = part("label");
    var model = part("model");
    function update() {
      var text = label ? label.value : "";
      var url = badgeUrl(base, kind.value, percentile.value, className.value, text, model ? model.value : "");
      part("preview").setAttribute("src", url);
      root.setAttribute("data-share-alt", altText(kind.value, text));
      if (share) share.fill(root, url);
      return url;
    }
    [kind, percentile, className, model].forEach(function (select) {
      if (select) select.addEventListener("change", update);
    });
    if (label) label.addEventListener("input", update);
    update();
    return update;
  }

  var api = { badgeUrl: badgeUrl, altText: altText, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-badge-url]").forEach(function (root) {
      setup(root, window.Share);
    });
  }
})();

/* The badge builder of the overview: an element with data-badge-url and the
   fields data-badge="kind|percentile|class|model|label|format", an <img data-badge="preview">
   and a link <a data-badge="json"> to the badge as JSON.
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

  /* The address of the badge in another format: svg, png or json. */
  function withFormat(url, format) {
    var wanted = ["svg", "png", "json"].indexOf(format) >= 0 ? format : "svg";
    return url.replace(/\.(svg|png|json)(\?|$)/, "." + wanted + "$2");
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
    var model = part("model"), format = part("format");
    function update() {
      var text = label ? label.value : "";
      var url = badgeUrl(base, kind.value, percentile.value, className.value, text, model ? model.value : "");
      url = withFormat(url, format ? format.value : "svg");
      part("preview").setAttribute("src", url);
      if (part("json")) part("json").setAttribute("href", withFormat(url, "json"));
      root.setAttribute("data-share-alt", altText(kind.value, text));
      if (share) share.fill(root, url);
      return url;
    }
    [kind, percentile, className, model, format].forEach(function (select) {
      if (select) select.addEventListener("change", update);
    });
    if (label) label.addEventListener("input", update);
    update();
    return update;
  }

  var api = { badgeUrl: badgeUrl, withFormat: withFormat, altText: altText, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-badge-url]").forEach(function (root) {
      setup(root, window.Share);
    });
  }
})();

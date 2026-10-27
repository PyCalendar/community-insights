/* The badge builder of the overview: an element with data-badge-url and the
   selects data-badge="kind|percentile|class", an <img data-badge="preview"> and a
   <textarea data-badge="markdown">. */
(function () {
  "use strict";

  /* The URL of a badge. The percentile is limited to 0-100. */
  function badgeUrl(base, kind, percentile, className) {
    var p = Number(percentile);
    if (!isFinite(p)) p = 50;
    p = Math.min(100, Math.max(0, p));
    var query = "?kind=" + (kind === "issue" ? "issue" : "pr") + "&percentile=" + p;
    if (className) query += "&class=" + encodeURIComponent(className);
    return base + query;
  }

  function markdown(url, kind) {
    var label = kind === "issue" ? "issue response time" : "pull request response time";
    return "![" + label + "](" + url + ")";
  }

  function setup(root) {
    var base = root.getAttribute("data-badge-url");
    function part(name) {
      return root.querySelector('[data-badge="' + name + '"]');
    }
    var kind = part("kind"), percentile = part("percentile"), className = part("class");
    function update() {
      var url = badgeUrl(base, kind.value, percentile.value, className.value);
      part("preview").setAttribute("src", url);
      part("markdown").value = markdown(url, kind.value);
    }
    [kind, percentile, className].forEach(function (select) {
      select.addEventListener("change", update);
    });
    update();
  }

  var api = { badgeUrl: badgeUrl, markdown: markdown, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-badge-url]").forEach(setup);
  }
})();

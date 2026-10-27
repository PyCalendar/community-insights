/* Share an image that links to the page it comes from, such as a badge or a
   chart: the code for Markdown, reStructuredText, HTML and the plain address.
   An element with data-share-image, data-share-link and data-share-alt fills
   its fields data-share="markdown|rst|html|link". */
(function () {
  "use strict";

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /* The code of each format: the image, with the page as the target of its link. */
  function formats(image, link, alt) {
    var text = String(alt || "").replace(/[\[\]\n]/g, " ").trim();
    return {
      markdown: "[![" + text + "](" + image + ")](" + link + ")",
      rst: ".. image:: " + image + "\n   :alt: " + text + "\n   :target: " + link,
      html: '<a href="' + escapeHtml(link) + '"><img src="' + escapeHtml(image) + '" alt="' + escapeHtml(text) + '"></a>',
      link: image,
    };
  }

  /* Fill the fields of an element; the image can be given when it changed. */
  function fill(root, image) {
    var source = image || root.getAttribute("data-share-image");
    var code = formats(source, root.getAttribute("data-share-link"), root.getAttribute("data-share-alt"));
    Object.keys(code).forEach(function (name) {
      var field = root.querySelector('[data-share="' + name + '"]');
      if (field) field.value = code[name];
    });
    return code;
  }

  var api = { escapeHtml: escapeHtml, formats: formats, fill: fill };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    window.Share = api;
    document.querySelectorAll("[data-share-image]").forEach(function (root) { fill(root); });
  }
})();

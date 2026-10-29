/* Copy buttons: data-copy="#id" copies the value or the text of that element,
   data-copy-url copies its value, the address to share, or else the address of
   the page. The button says "Copied" for a
   moment. */
(function () {
  "use strict";

  /* A text in the language of the page (Django's JavaScript catalog). */
  function _(text) {
    return typeof gettext === "function" ? gettext(text) : text;
  }

  /* The text a button copies. */
  function textOf(button, doc, location) {
    if (button.hasAttribute("data-copy-url")) return button.getAttribute("data-copy-url") || String(location.href);
    var target = doc.querySelector(button.getAttribute("data-copy"));
    if (!target) return "";
    return target.value !== undefined ? target.value : target.textContent;
  }

  /* Copy with the clipboard of the browser; selecting the field is the fallback. */
  function copy(text, clipboard) {
    if (clipboard && clipboard.writeText) return clipboard.writeText(text);
    return Promise.reject(new Error("no clipboard"));
  }

  function confirmCopied(button, wait) {
    var label = button.getAttribute("data-copy-label") || button.textContent;
    button.setAttribute("data-copy-label", label);
    button.textContent = _("Copied");
    wait(function () { button.textContent = label; }, 2000);
  }

  function setup(doc, win) {
    doc.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("[data-copy], [data-copy-url]");
      if (!button) return;
      event.preventDefault();
      var text = textOf(button, doc, win.location);
      copy(text, win.navigator && win.navigator.clipboard).then(
        function () { confirmCopied(button, win.setTimeout.bind(win)); },
        function () {
          var target = button.hasAttribute("data-copy") && doc.querySelector(button.getAttribute("data-copy"));
          if (target && target.select) target.select();
        }
      );
    });
  }

  var api = { textOf: textOf, copy: copy, confirmCopied: confirmCopied, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    setup(document, window);
  }
})();

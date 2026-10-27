/* Ask before something is deleted: a form or button with data-confirm="question"
   is only sent when the question is answered with OK. */
(function () {
  "use strict";

  /* Whether to go on with an event of an element: true without data-confirm. */
  function allowed(element, ask) {
    var question = element && element.getAttribute && element.getAttribute("data-confirm");
    return !question || Boolean(ask(question));
  }

  function setup(doc, ask) {
    doc.addEventListener("submit", function (event) {
      if (!allowed(event.target, ask)) event.preventDefault();
    });
    doc.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("button[data-confirm]");
      if (button && !allowed(button, ask)) event.preventDefault();
    });
  }

  var api = { allowed: allowed, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    setup(document, function (question) { return window.confirm(question); });
  }
})();

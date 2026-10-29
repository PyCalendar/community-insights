/* Running a query (Enter or the button) scrolls the page down, so that the
   query is at the top of the window and its result shows below it:
   <form data-scroll-on-submit>. htmx puts the result in without loading the
   page, so the page would stay where it was. */
(function () {
  "use strict";

  function setup(form) {
    form.addEventListener("submit", function () {
      form.scrollIntoView({ block: "start", behavior: "smooth" });
    });
  }

  var api = { setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-scroll-on-submit]").forEach(setup);
  }
})();

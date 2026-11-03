/* A choice that takes effect at once: <select data-submit-on-change> sends its form when
   another option is chosen, such as the language in the footer. Without JavaScript, the
   form has its own button. */
(function () {
  "use strict";

  function setup(select) {
    select.addEventListener("change", function () {
      if (select.form) select.form.requestSubmit();
    });
  }

  var api = { setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-submit-on-change]").forEach(setup);
  }
})();

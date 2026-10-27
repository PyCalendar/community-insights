/* The switch between the names of the columns of the contributors table as
   variables and in words: <input data-column-names="#table"> sets data-names
   of the table to "variables" or "words"; the choice is kept in the browser. */
(function () {
  "use strict";

  var KEY = "column-names";

  /* The names to show for the state of the switch. */
  function namesFor(checked) {
    return checked ? "words" : "variables";
  }

  /* The kept choice, "variables" when there is none or the storage is blocked. */
  function kept(storage) {
    try {
      return storage && storage.getItem(KEY) === "words" ? "words" : "variables";
    } catch (error) {
      return "variables";
    }
  }

  function keep(storage, names) {
    try {
      if (storage) storage.setItem(KEY, names);
    } catch (error) {
      /* the switch works for this page */
    }
  }

  function setup(input, doc, storage) {
    var table = doc.querySelector(input.getAttribute("data-column-names"));
    if (!table) return null;
    input.checked = kept(storage) === "words";
    table.setAttribute("data-names", namesFor(input.checked));
    input.addEventListener("change", function () {
      var names = namesFor(input.checked);
      table.setAttribute("data-names", names);
      keep(storage, names);
    });
    return table;
  }

  var api = { namesFor: namesFor, kept: kept, keep: keep, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    var storage = null;
    try { storage = window.localStorage; } catch (error) { storage = null; }
    document.querySelectorAll("[data-column-names]").forEach(function (input) {
      setup(input, document, storage);
    });
  }
})();

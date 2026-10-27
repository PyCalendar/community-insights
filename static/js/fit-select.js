/* The choice of the statistic of a table of response times: a <select
   data-fit-select="#table"> shows only the rows <tr data-fit="..."> of the
   chosen fit; the empty choice shows all. Without JavaScript all rows show. */
(function () {
  "use strict";

  /* Show the rows of one fit, or all rows for "". Returns how many are shown. */
  function show(rows, fit) {
    var shown = 0;
    Array.prototype.forEach.call(rows, function (row) {
      var visible = !fit || row.getAttribute("data-fit") === fit;
      row.hidden = !visible;
      if (visible) shown++;
    });
    return shown;
  }

  function setup(select, doc) {
    var table = doc.querySelector(select.getAttribute("data-fit-select"));
    if (!table) return null;
    function update() {
      return show(table.querySelectorAll("tr[data-fit]"), select.value);
    }
    select.addEventListener("change", update);
    update();
    return update;
  }

  var api = { show: show, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-fit-select]").forEach(function (select) {
      setup(select, document);
    });
  }
})();

/* Lists to put in order by drag and drop, with Sortable.js (mouse, touch and pen).
   A list [data-sort-list] holds items [data-sort-id], dragged by their handle
   [data-sort-handle]. After a drop, the ids in their new order are sent as
   "order" fields of the form whose id is in data-sort-form. The arrow buttons
   of the items do the same without dragging, also for keyboards. */
(function () {
  "use strict";

  /* The ids of the items of a list, from top to bottom. */
  function ids(list) {
    return Array.prototype.map.call(list.querySelectorAll("[data-sort-id]"), function (item) {
      return item.getAttribute("data-sort-id");
    });
  }

  /* Put the ids into the form as "order" fields, replacing earlier ones. */
  function fill(form, order) {
    Array.prototype.forEach.call(form.querySelectorAll('input[name="order"]'), function (input) {
      input.parentNode.removeChild(input);
    });
    order.forEach(function (id) {
      var input = form.ownerDocument.createElement("input");
      input.type = "hidden";
      input.name = "order";
      input.value = id;
      form.appendChild(input);
    });
    return form;
  }

  /* Make a list sortable; a drop that moved an item sends the form. */
  function setup(list, Sortable) {
    var form = list.ownerDocument.getElementById(list.getAttribute("data-sort-form"));
    if (!form || !Sortable) return null;
    return Sortable.create(list, {
      handle: "[data-sort-handle]",
      draggable: "[data-sort-id]",
      animation: 150,
      onEnd: function (event) {
        if (event.oldIndex === event.newIndex) return;
        fill(form, ids(list)).submit();
      },
    });
  }

  var api = { ids: ids, fill: fill, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-sort-list]").forEach(function (list) {
      setup(list, window.Sortable);
    });
  }
})();

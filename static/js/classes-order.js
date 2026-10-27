/* The order of the classes of people by drag and drop: the cards
   [data-class-id] in [data-class-order] are dragged by their handle
   [data-drag-class]; a drop sends the new order with the form
   [data-class-order-form]. The arrow buttons of the cards do the same without a mouse. */
(function () {
  "use strict";

  /* The ids with the dragged one at the place of the target. */
  function reorder(ids, dragged, target) {
    var from = ids.indexOf(dragged), to = ids.indexOf(target);
    if (from < 0 || to < 0 || from === to) return ids.slice();
    var result = ids.slice();
    result.splice(from, 1);
    result.splice(to, 0, dragged);
    return result;
  }

  /* Put the ids into the form as "order" fields, replacing earlier ones. */
  function fill(form, ids) {
    Array.prototype.forEach.call(form.querySelectorAll('input[name="order"]'), function (input) {
      input.parentNode.removeChild(input);
    });
    ids.forEach(function (id) {
      var input = form.ownerDocument.createElement("input");
      input.type = "hidden";
      input.name = "order";
      input.value = id;
      form.appendChild(input);
    });
    return form;
  }

  function setup(root, form) {
    var dragged = null;
    function ids() {
      return Array.prototype.map.call(root.querySelectorAll("[data-class-id]"), function (card) {
        return card.getAttribute("data-class-id");
      });
    }
    root.addEventListener("dragstart", function (event) {
      var handle = event.target.closest && event.target.closest("[data-drag-class]");
      var card = handle && handle.closest("[data-class-id]");
      dragged = card ? card.getAttribute("data-class-id") : null;
      if (dragged && event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", dragged);
      }
    });
    root.addEventListener("dragover", function (event) {
      if (dragged) event.preventDefault();
    });
    root.addEventListener("drop", function (event) {
      var card = event.target.closest && event.target.closest("[data-class-id]");
      if (!dragged || !card) return;
      event.preventDefault();
      var next = reorder(ids(), dragged, card.getAttribute("data-class-id"));
      dragged = null;
      fill(form, next).submit();
    });
  }

  var api = { reorder: reorder, fill: fill, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    var form = document.querySelector("[data-class-order-form]");
    document.querySelectorAll("[data-class-order]").forEach(function (root) { setup(root, form); });
  }
})();

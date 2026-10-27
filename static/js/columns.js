/* The columns of the contributors table: a text field data-columns-input
   (names separated by spaces) becomes a list to reorder by drag and drop or the
   arrow buttons, with a remove button per column and a select to add one. The
   default columns are in data-columns-default; an unchanged default stays "". */
(function () {
  "use strict";

  function _(text) {
    return typeof gettext === "function" ? gettext(text) : text;
  }

  function t(text, values) {
    return text.replace(/%\((\w+)\)s/g, function (all, name) { return String(values[name]); });
  }

  /* The columns of a text, or the defaults for an empty one. */
  function parse(text, defaults) {
    var names = String(text || "").replace(/,/g, " ").split(/\s+/).filter(Boolean);
    return names.length ? names : defaults.slice();
  }

  /* The text of the columns: "" while they are the defaults. */
  function serialize(columns, defaults) {
    return columns.join(" ") === defaults.join(" ") ? "" : columns.join(" ");
  }

  /* The columns with one moved by delta places, kept inside the list. */
  function move(columns, index, delta) {
    var to = Math.min(columns.length - 1, Math.max(0, index + delta));
    var result = columns.slice();
    var name = result.splice(index, 1)[0];
    result.splice(to, 0, name);
    return result;
  }

  /* The columns with one moved to the place of another (drag and drop). */
  function moveTo(columns, from, to) {
    return move(columns, from, to - from);
  }

  function remove(columns, index) {
    return columns.filter(function (_name, i) { return i !== index; });
  }

  /* The columns with a name added at the end, once. */
  function add(columns, name) {
    if (!name || columns.indexOf(name) >= 0) return columns.slice();
    return columns.concat([name]);
  }

  function button(doc, text, label, action) {
    var element = doc.createElement("button");
    element.type = "button";
    element.className = "btn btn-link btn-sm p-0 px-1";
    element.textContent = text;
    element.setAttribute("aria-label", label);
    element.setAttribute("data-column-action", action);
    return element;
  }

  function setup(input) {
    var doc = input.ownerDocument;
    var defaults = (input.getAttribute("data-columns-default") || "").split(/\s+/).filter(Boolean);
    var names = (input.getAttribute("data-columns-names") || "").split(/\s+/).filter(Boolean);
    var columns = parse(input.value, defaults);
    var list = doc.createElement("ul");
    list.className = "column-list list-unstyled d-flex flex-wrap gap-1 mb-1";
    var choose = doc.createElement("select");
    choose.className = "form-select form-select-sm w-auto";
    choose.setAttribute("aria-label", _("Add a column"));
    var dragged = null;

    function change(next) {
      columns = next;
      input.value = serialize(columns, defaults);
      draw();
    }

    function draw() {
      list.textContent = "";
      columns.forEach(function (name, index) {
        var item = doc.createElement("li");
        item.className = "column-chip";
        item.draggable = true;
        item.setAttribute("data-column", name);
        var label = doc.createElement("span");
        label.className = "font-monospace";
        label.textContent = name;
        item.appendChild(button(doc, "‹", t(_("Move %(name)s left"), { name: name }), "left"));
        item.appendChild(label);
        item.appendChild(button(doc, "›", t(_("Move %(name)s right"), { name: name }), "right"));
        item.appendChild(button(doc, "×", t(_("Remove %(name)s"), { name: name }), "remove"));
        item.addEventListener("click", function (event) {
          var action = event.target.getAttribute && event.target.getAttribute("data-column-action");
          if (action === "left") change(move(columns, index, -1));
          if (action === "right") change(move(columns, index, 1));
          if (action === "remove") change(remove(columns, index));
        });
        item.addEventListener("dragstart", function () { dragged = index; });
        item.addEventListener("dragover", function (event) { event.preventDefault(); });
        item.addEventListener("drop", function (event) {
          event.preventDefault();
          if (dragged !== null && dragged !== index) change(moveTo(columns, dragged, index));
          dragged = null;
        });
        list.appendChild(item);
      });
      choose.textContent = "";
      var first = doc.createElement("option");
      first.value = "";
      first.textContent = _("+ add a column");
      choose.appendChild(first);
      names.forEach(function (name) {
        if (columns.indexOf(name) >= 0) return;
        var option = doc.createElement("option");
        option.value = name;
        option.textContent = name;
        choose.appendChild(option);
      });
    }

    choose.addEventListener("change", function () {
      change(add(columns, choose.value));
    });
    input.hidden = true;
    input.parentNode.insertBefore(list, input.nextSibling);
    input.parentNode.insertBefore(choose, list.nextSibling);
    draw();
    return { list: list, choose: choose, columns: function () { return columns; } };
  }

  var api = {
    parse: parse, serialize: serialize, move: move, moveTo: moveTo, remove: remove, add: add, setup: setup,
  };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-columns-input]").forEach(setup);
  }
})();

/* The source picker: a text field that filters the projects and suggested
   repositories and organisations (listed first: projects, then those of the
   user, their organisations and what they contributed to). Text that is not in
   the list can be added as owner/name or owner. */
(function () {
  "use strict";

  /* A text in the language of the page (Django's JavaScript catalog); in
     node, the English text. `_` is the name xgettext looks for. */
  function _(text) {
    return typeof gettext === "function" ? gettext(text) : text;
  }

  /* A translated text with %(name)s replaced by the values. */
  function t(text, values) {
    return text.replace(/%\((\w+)\)s/g, function (all, name) { return String(values[name]); });
  }

  /* The label of a kind of source. */
  function kindLabel(kind) {
    var labels = {
      project: _("project"), yours: _("yours"), organisation: _("organisation"),
      contributed: _("contributed"), new: _("new"),
    };
    return labels[kind] || kind;
  }

  var KIND_ORDER = { project: 0, yours: 1, organisation: 2, contributed: 3 };
  var TARGET = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\/[A-Za-z0-9._-]{1,100})?$/;

  /* "owner/name", "owner", or a GitHub URL of them; null if it is none. */
  function asTarget(text) {
    var value = String(text || "").trim()
      .replace(/^https?:\/\/(www\.)?github\.com\//i, "")
      .replace(/\.git$/, "")
      .replace(/\/+$/, "");
    return TARGET.test(value) ? value : null;
  }

  function rank(kind) {
    return Object.prototype.hasOwnProperty.call(KIND_ORDER, kind) ? KIND_ORDER[kind] : 9;
  }

  /* The choices that contain the text (any case), best first: those that start
     with it, then by kind, whole organisations before repositories, then by
     stars, then by name. */
  function filter(choices, text, limit) {
    var needle = String(text || "").trim().toLowerCase();
    var found = choices.filter(function (choice) {
      return !needle || choice.name.toLowerCase().indexOf(needle) >= 0;
    });
    found.sort(function (a, b) {
      var aStarts = needle && a.name.toLowerCase().indexOf(needle) === 0 ? 0 : 1;
      var bStarts = needle && b.name.toLowerCase().indexOf(needle) === 0 ? 0 : 1;
      return aStarts - bStarts ||
        rank(a.kind) - rank(b.kind) ||
        (a.name.indexOf("/") >= 0) - (b.name.indexOf("/") >= 0) ||
        (b.stars || 0) - (a.stars || 0) ||
        a.name.localeCompare(b.name);
    });
    return found.slice(0, limit || 20);
  }

  /* Whether to offer "Add <text>": a valid target that is not listed exactly. */
  function offerToAdd(choices, text) {
    var target = asTarget(text);
    if (!target) return null;
    var lower = target.toLowerCase();
    var listed = choices.some(function (choice) { return choice.name.toLowerCase() === lower; });
    return listed ? null : target;
  }

  function setup(root) {
    var choices = JSON.parse(root.querySelector('script[type="application/json"]').textContent);
    var input = root.querySelector("[data-sources=input]");
    var list = root.querySelector("[data-sources=list]");
    var target = root.querySelector("[data-sources=target]");
    var doc = root.ownerDocument;

    function button(label, value, kind) {
      var item = doc.createElement("button");
      item.type = "submit";
      item.className = "list-group-item list-group-item-action d-flex justify-content-between";
      item.setAttribute("data-value", value);
      var name = doc.createElement("span");
      name.textContent = label;
      var badge = doc.createElement("small");
      badge.className = "text-muted";
      badge.textContent = kindLabel(kind);
      item.appendChild(name);
      item.appendChild(badge);
      item.addEventListener("click", function () { target.value = value; });
      return item;
    }

    function update() {
      list.textContent = "";
      var add = offerToAdd(choices, input.value);
      if (add) list.appendChild(button(t(_("Add %(target)s"), { target: add }), add, "new"));
      filter(choices, input.value, 12).forEach(function (choice) {
        list.appendChild(button(choice.name, choice.name, choice.kind));
      });
    }
    input.addEventListener("input", update);
    update();
    return update;
  }

  var api = {
    asTarget: asTarget, filter: filter, offerToAdd: offerToAdd, kindLabel: kindLabel, setup: setup,
  };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-sources]").forEach(function (root) {
      if (root.getAttribute("data-sources") === "picker") setup(root);
    });
  }
})();

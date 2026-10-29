/* Completion of the names of variables in the query field of the contributors
   page: <input data-complete-words="name ..."> shows the names that start with
   the word at the cursor. Tab takes the first one; the arrows choose one, which
   Enter takes. Otherwise Enter runs the query, as in any form. Escape closes. */
(function () {
  "use strict";

  var WORD = /[A-Za-z_]/;

  /* The word that ends at the cursor: where it starts and ends, and its text. */
  function wordAt(text, cursor) {
    var start = cursor;
    while (start > 0 && WORD.test(text[start - 1])) start--;
    var end = cursor;
    while (end < text.length && WORD.test(text[end])) end++;
    return { start: start, end: end, word: text.slice(start, cursor) };
  }

  /* The words that start with the prefix, not the prefix itself, at most limit. */
  function suggestions(words, prefix, limit) {
    if (!prefix) return [];
    var lower = prefix.toLowerCase();
    return words
      .filter(function (word) { return word.toLowerCase().indexOf(lower) === 0 && word !== prefix; })
      .slice(0, limit || 8);
  }

  /* Whether a key takes a suggestion: Tab the chosen or the first one, Enter
     only one chosen with the arrows, so that Enter runs the query otherwise. */
  function takes(key, active, count) {
    if (!count) return false;
    if (key === "Tab") return true;
    return key === "Enter" && active >= 0;
  }

  /* The text with the word at start..end replaced and where the cursor goes. */
  function replaceWord(text, start, end, word) {
    var after = text.slice(end);
    var space = after && after[0] === " " ? "" : " ";
    return { text: text.slice(0, start) + word + space + after, cursor: start + word.length + 1 };
  }

  function setup(input) {
    var doc = input.ownerDocument;
    var words = (input.getAttribute("data-complete-words") || "").split(/\s+/).filter(Boolean);
    var list = doc.createElement("ul");
    list.className = "complete-list list-group";
    list.id = input.id + "-complete";
    list.setAttribute("role", "listbox");
    list.hidden = true;
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", list.id);
    input.parentNode.classList.add("complete-host");
    input.parentNode.appendChild(list);
    var shown = [], active = -1, word = null;

    function close() {
      list.hidden = true;
      shown = [];
      active = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }

    function take(index) {
      var result = replaceWord(input.value, word.start, word.end, shown[index]);
      input.value = result.text;
      input.setSelectionRange(result.cursor, result.cursor);
      close();
      input.focus();
    }

    function draw() {
      list.textContent = "";
      shown.forEach(function (name, index) {
        var item = doc.createElement("li");
        item.className = "list-group-item list-group-item-action py-1 font-monospace" + (index === active ? " active" : "");
        item.id = list.id + "-" + index;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", index === active ? "true" : "false");
        item.textContent = name;
        item.addEventListener("mousedown", function (event) {
          event.preventDefault();
          take(index);
        });
        list.appendChild(item);
      });
      list.hidden = !shown.length;
      input.setAttribute("aria-expanded", shown.length ? "true" : "false");
      if (active >= 0) input.setAttribute("aria-activedescendant", list.id + "-" + active);
    }

    function suggest() {
      word = wordAt(input.value, input.selectionStart);
      shown = suggestions(words, word.word);
      active = -1;
      draw();
    }

    input.addEventListener("input", suggest);
    input.addEventListener("keydown", function (event) {
      if (list.hidden) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        active = (active + (event.key === "ArrowDown" ? 1 : shown.length - 1)) % shown.length;
        draw();
      } else if (takes(event.key, active, shown.length)) {
        event.preventDefault();
        take(Math.max(active, 0));
      } else if (event.key === "Enter") {
        close();  // the form is sent: the query runs
      } else if (event.key === "Escape") {
        close();
      }
    });
    input.addEventListener("blur", close);
    // typed before the script ran, while the page was still loading
    if (doc.activeElement === input && input.value) suggest();
    return list;
  }

  var api = { wordAt: wordAt, suggestions: suggestions, takes: takes, replaceWord: replaceWord, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-complete-words]").forEach(setup);
  }
})();

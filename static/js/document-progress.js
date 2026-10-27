/* The page of a document made in the background: polls the address of
   data-document-progress until the file is ready or failed, moves the bar
   [data-document-bar] and shows the download [data-document-download] or the
   error [data-document-error]. */
(function () {
  "use strict";

  function _(text) {
    return typeof gettext === "function" ? gettext(text) : text;
  }

  /* Whether to ask again: while the document is queued or being made. */
  function waiting(status) {
    return status === "queued" || status === "running";
  }

  /* The text of the state of a document. */
  function stateText(answer) {
    if (answer.status === "done") return _("The file is ready.");
    if (answer.status === "failed") return _("The file could not be made.");
    return _("The file is being made from the data on this site.");
  }

  function show(root, answer) {
    var bar = root.querySelector("[data-document-bar]");
    var inner = bar && bar.firstElementChild;
    var percent = Math.max(0, Math.min(100, Number(answer.progress) || 0));
    if (bar) bar.setAttribute("aria-valuenow", String(percent));
    if (inner) {
      inner.style.width = percent + "%";
      inner.textContent = percent + " %";
    }
    var state = root.querySelector("[data-document-state]");
    if (state && !waiting(answer.status)) state.textContent = stateText(answer);
    var download = root.querySelector("[data-document-download]");
    if (download) download.hidden = answer.status !== "done";
    var error = root.querySelector("[data-document-error]");
    if (error && answer.status === "failed") {
      error.hidden = false;
      error.textContent = answer.message || stateText(answer);
    }
  }

  function setup(root, fetchJson, later) {
    var address = root.getAttribute("data-document-progress");
    function ask() {
      return fetchJson(address).then(function (answer) {
        show(root, answer);
        if (waiting(answer.status)) later(ask, 1000);
        return answer;
      }, function () {
        later(ask, 5000);  /* the server did not answer: try again later */
      });
    }
    return ask();
  }

  var api = { waiting: waiting, stateText: stateText, show: show, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-document-progress]").forEach(function (root) {
      setup(
        root,
        function (address) {
          return fetch(address, { credentials: "same-origin" }).then(function (r) {
            if (!r.ok) throw new Error(String(r.status));
            return r.json();
          });
        },
        function (f, ms) { window.setTimeout(f, ms); }
      );
    });
  }
})();

/* The data bar of a statistics page: how complete the data is, how long until
   it is complete and which fetches run. Polls data-progress-url while fetches
   are active. */
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

  /* Two units at most: 45min, 3h 12min, 2d 4h; "< 1min" below a minute. */
  function formatDuration(seconds) {
    if (seconds === null || seconds === undefined || !isFinite(seconds)) return "";
    var minutes = Math.round(Math.max(0, seconds) / 60);
    if (minutes < 1) return "< 1min";
    var days = Math.floor(minutes / 1440);
    minutes -= days * 1440;
    var hours = Math.floor(minutes / 60);
    minutes -= hours * 60;
    if (days) return hours ? days + "d " + hours + "h" : days + "d";
    if (hours) return minutes ? hours + "h " + minutes + "min" : hours + "h";
    return minutes + "min";
  }

  /* The text next to the bar. */
  function describe(state) {
    var percent = Math.max(0, Math.min(100, Math.round(state.percent || 0)));
    var text = t(_("%(percent)s% of the data"), { percent: percent });
    if (state.total !== null && state.total !== undefined) {
      text = t(_("%(percent)s% of the data (%(items)s of %(total)s items)"),
        { percent: percent, items: state.items, total: state.total });
    }
    var active = (state.jobs || []).filter(function (job) {
      return job.status === "running" || job.status === "queued";
    });
    if (active.length) {
      var left = formatDuration(state.seconds_left);
      text += left ? t(_(", complete in about %(left)s"), { left: left }) : _(", reading");
    } else if (percent < 100) {
      text += _(", read from GitHub to complete it");
    }
    return { percent: percent, text: text, active: active.length > 0 };
  }

  function render(root, state) {
    var shown = describe(state);
    var bar = root.querySelector("[data-progress=bar]");
    bar.style.width = shown.percent + "%";
    bar.setAttribute("aria-valuenow", String(shown.percent));
    root.querySelector("[data-progress=text]").textContent = shown.text;
    var list = root.querySelector("[data-progress=jobs]");
    if (list) {
      list.textContent = "";
      (state.jobs || []).forEach(function (job) {
        var item = root.ownerDocument.createElement("li");
        item.textContent = job.repository + ": " + job.status + " " + job.percent + "%" +
          (job.message ? " (" + job.message + ")" : "");
        list.appendChild(item);
      });
    }
    return shown;
  }

  /* An error of the site, {"error": {title, detail, docs_url}}, or null when
     the site could not be reached at all. */
  function describeError(answer) {
    var error = answer && answer.error;
    if (!error) {
      return { text: _("The site cannot be reached right now; trying again."), link: null };
    }
    return { text: error.title + ": " + error.detail, link: error.docs_url || null };
  }

  function renderError(root, answer) {
    var shown = describeError(answer);
    var place = root.querySelector("[data-progress=text]");
    place.textContent = shown.text + " ";
    if (shown.link) {
      var link = root.ownerDocument.createElement("a");
      link.href = shown.link;
      link.textContent = _("What to do");
      place.appendChild(link);
    }
    return shown;
  }

  function setup(root, fetchJson, schedule) {
    var url = root.getAttribute("data-progress-url");
    var interval = Number(root.getAttribute("data-progress-interval")) || 4000;
    var wasActive = root.getAttribute("data-progress-active") === "true";
    function poll() {
      return fetchJson(url).then(function (state) {
        var shown = render(root, state);
        if (shown.active) schedule(poll, interval);
        else if (wasActive && root.ownerDocument.defaultView) {
          // the fetch ended: show the statistics of the new data
          root.ownerDocument.defaultView.location.reload();
        }
        wasActive = shown.active;
      }, function (answer) {
        renderError(root, answer);
        schedule(poll, interval * 2);
      });
    }
    if (wasActive) schedule(poll, interval);
    return poll;
  }

  var api = {
    formatDuration: formatDuration, describe: describe, render: render,
    describeError: describeError, renderError: renderError, setup: setup,
  };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    document.querySelectorAll("[data-progress-url]").forEach(function (root) {
      setup(
        root,
        function (url) {
          return fetch(url, { credentials: "same-origin" }).then(function (r) {
            if (r.ok) return r.json();
            // an error of the site comes as JSON with what to do
            return r.json().then(function (body) { throw body; }, function () { throw null; });
          });
        },
        function (f, ms) { setTimeout(f, ms); }
      );
    });
  }
})();

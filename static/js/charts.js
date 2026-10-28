/* Interactive charts with Chart.js: an <img data-chart-json="..."> of a chart
   (the SVG of the server) is replaced by a canvas that Chart.js draws from the
   data of its address, with tooltips. The heat map uses chartjs-chart-matrix.
   Without JavaScript, or when the data cannot be read, the SVG stays. When the
   theme of the page changes, the charts are drawn again in its colours. */
(function () {
  "use strict";

  /* Hours as 10min, 6h 30min, 2d 4h; 0 as "0". */
  function formatHours(hours) {
    if (!hours) return "0";
    var minutes = Math.round(hours * 60);
    if (minutes < 1) return "< 1min";
    var days = Math.floor(minutes / 1440);
    minutes -= days * 1440;
    var whole = Math.floor(minutes / 60);
    minutes -= whole * 60;
    if (days) return whole ? days + "d " + whole + "h" : days + "d";
    if (whole) return minutes ? whole + "h " + minutes + "min" : whole + "h";
    return minutes + "min";
  }

  /* The address with the theme of the page; other parameters stay. */
  function withTheme(address, theme) {
    var base = address.replace(/([?&])theme=[a-z]*(&|$)/, function (all, before, after) {
      return after ? before : "";
    });
    return base + (base.indexOf("?") >= 0 ? "&" : "?") + "theme=" + theme;
  }

  function hex(color) {
    var value = parseInt(color.slice(1), 16);
    return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
  }

  /* The colour of a share (0 to 1) between the stops, from few to many. */
  function heatColor(stops, share) {
    var position = Math.max(0, Math.min(1, share || 0)) * (stops.length - 1);
    var index = Math.min(stops.length - 2, Math.floor(position));
    var from = hex(stops[index]), to = hex(stops[index + 1]), part = position - index;
    var mixed = from.map(function (start, i) { return Math.round(start + (to[i] - start) * part); });
    return "rgb(" + mixed.join(", ") + ")";
  }

  function axis(title, ink, extra) {
    var shown = {
      title: { display: !!title, text: title, color: ink },
      ticks: { color: ink },
      grid: { color: "rgba(127, 127, 127, 0.15)" },
    };
    Object.keys(extra || {}).forEach(function (key) { shown[key] = extra[key]; });
    return shown;
  }

  /* The configuration of Chart.js for the data of chart_data.py. */
  function toConfig(data) {
    var ink = data.ink;
    var datasets = data.datasets.map(function (dataset) {
      var copy = {};
      Object.keys(dataset).forEach(function (key) { copy[key] = dataset[key]; });
      return copy;
    });
    var options = {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      indexAxis: data.horizontal ? "y" : "x",
      plugins: {
        title: { display: !!data.title, text: data.title, color: ink },
        legend: { display: datasets.length > 1, labels: { color: ink } },
        tooltip: {},
      },
      scales: {
        x: axis(data.x, ink, { stacked: !!data.stacked }),
        y: axis(data.y, ink, { stacked: !!data.stacked, beginAtZero: true }),
      },
    };
    if (data.durations) {
      options.scales[data.durations].ticks.callback = function (value) { return formatHours(value); };
      options.plugins.tooltip.callbacks = {
        label: function (item) {
          var counts = item.dataset.counts;
          var text = formatHours(item.parsed[data.durations]);
          return counts ? text + " (" + counts[item.dataIndex] + ")" : text;
        },
      };
    }
    if (data.type === "matrix") {
      var cells = datasets[0];
      var most = Math.max.apply(null, cells.data.map(function (cell) { return cell.v; }).concat([1]));
      cells.backgroundColor = function (context) {
        var cell = context.dataset.data[context.dataIndex];
        return heatColor(data.heat, cell ? cell.v / most : 0);
      };
      cells.width = function (context) {
        var area = context.chart.chartArea;
        return area ? area.width / data.labels.length - 1 : 0;
      };
      cells.height = function (context) {
        var area = context.chart.chartArea;
        return area ? area.height / data.rows.length - 1 : 0;
      };
      options.scales.x = axis(data.x, ink, { type: "category", labels: data.labels, offset: true });
      options.scales.y = axis(data.y, ink, { type: "category", labels: data.rows, offset: true });
      options.plugins.tooltip.callbacks = {
        title: function () { return ""; },
        label: function (item) {
          var cell = item.dataset.data[item.dataIndex];
          return cell.y + " " + cell.x + ": " + cell.v;
        },
      };
    }
    return { type: data.type, data: { labels: data.labels, datasets: datasets }, options: options };
  }

  /* The theme of the page: light or dark. */
  function themeOf(doc) {
    return doc.documentElement.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
  }

  /* Draw the chart of an image with Chart.js; the image stays when there is no data. */
  function setup(img, Chart, fetchJson) {
    var doc = img.ownerDocument;
    img.setAttribute("data-chart-ready", "");
    var state = { img: img, chart: null, asked: 0 };
    function draw() {
      var theme = themeOf(doc);
      var asked = ++state.asked;
      return fetchJson(withTheme(img.getAttribute("data-chart-json"), theme)).then(function (data) {
        if (asked !== state.asked) return state.chart;  /* a newer draw, such as of a new theme */
        if (state.chart) state.chart.destroy();
        if (data.empty) return null;
        var box = state.box;
        if (!box) {
          box = state.box = doc.createElement("div");
          box.className = "chart-canvas";
          box.style.position = "relative";
          box.style.height = (data.type === "matrix" ? 16 : 18) + "rem";
          var canvas = doc.createElement("canvas");
          canvas.setAttribute("role", "img");
          canvas.setAttribute("aria-label", img.getAttribute("alt") || "");
          box.appendChild(canvas);
          img.parentNode.insertBefore(box, img.nextSibling);
        }
        img.hidden = true;
        box.setAttribute("data-chart-theme", theme);
        state.chart = new Chart(box.firstChild, toConfig(data));
        return state.chart;
      }, function () {
        return null;  /* the SVG stays */
      });
    }
    state.draw = draw;
    return state;
  }

  var api = {
    formatHours: formatHours, withTheme: withTheme, heatColor: heatColor, toConfig: toConfig,
    themeOf: themeOf, setup: setup,
  };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else if (window.Chart) {
    var fetchJson = function (address) {
      return fetch(address, { credentials: "same-origin" }).then(function (answer) {
        if (!answer.ok) throw new Error(String(answer.status));
        return answer.json();
      });
    };
    var drawn = [];
    var drawNew = function () {
      document.querySelectorAll("img[data-chart-json]:not([data-chart-ready])").forEach(function (img) {
        var state = setup(img, window.Chart, fetchJson);
        drawn.push(state);
        state.draw();
      });
    };
    drawNew();
    document.addEventListener("htmx:afterSettle", drawNew);  /* the result of a query */
    new MutationObserver(function () {
      /* also charts still being drawn; those htmx replaced are gone */
      drawn = drawn.filter(function (state) { return state.img.isConnected; });
      drawn.forEach(function (state) { state.draw(); });
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-bs-theme"] });
  }
})();

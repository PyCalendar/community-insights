const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { JSDOM } = require("jsdom");
const charts = require("../../static/js/charts.js");

const BARS = {
  type: "bar", labels: ["1h", "3h"], x: "time", y: "responses", ink: "#4d5f4d", empty: false,
  datasets: [{ label: "bot", data: [2, 0], backgroundColor: "#9ccc9c" }, { label: "maintainer", data: [0, 1] }],
};

test("formatHours shows durations as on the SVG", () => {
  assert.equal(charts.formatHours(0), "0");
  assert.equal(charts.formatHours(1 / 6), "10min");
  assert.equal(charts.formatHours(6.5), "6h 30min");
  assert.equal(charts.formatHours(52), "2d 4h");
  assert.equal(charts.formatHours(0.001), "< 1min");
});

test("withTheme replaces or adds the theme", () => {
  assert.equal(charts.withTheme("/s/1/chart/hours.json?login=bob", "dark"), "/s/1/chart/hours.json?login=bob&theme=dark");
  assert.equal(charts.withTheme("/c.json?theme=dark&x=1", "light"), "/c.json?x=1&theme=light");
  assert.equal(charts.withTheme("/c.json", "light"), "/c.json?theme=light");
});

test("heatColor goes from the first to the last stop", () => {
  const stops = ["#000000", "#ffffff"];
  assert.equal(charts.heatColor(stops, 0), "rgb(0, 0, 0)");
  assert.equal(charts.heatColor(stops, 1), "rgb(255, 255, 255)");
  assert.equal(charts.heatColor(stops, 0.5), "rgb(128, 128, 128)");
  assert.equal(charts.heatColor(stops, 7), "rgb(255, 255, 255)", "kept inside");
});

test("toConfig gives Chart.js the bars, the titles and the colours of the theme", () => {
  const config = charts.toConfig(BARS);
  assert.equal(config.type, "bar");
  assert.deepEqual(config.data.labels, ["1h", "3h"]);
  assert.equal(config.options.scales.x.title.text, "time");
  assert.equal(config.options.scales.y.ticks.color, "#4d5f4d");
  assert.equal(config.options.plugins.legend.display, true, "two series");
  assert.equal(config.options.indexAxis, "x");
  assert.equal(charts.toConfig({ ...BARS, horizontal: true }).options.indexAxis, "y");
});

test("toConfig shows hours as durations, with the number of responses", () => {
  const config = charts.toConfig({
    type: "line", labels: ["2026-01"], ink: "#000", durations: "y",
    datasets: [{ label: "median", data: [6.5], counts: [4] }],
  });
  assert.equal(config.options.scales.y.ticks.callback(24), "1d");
  const label = config.options.plugins.tooltip.callbacks.label;
  assert.equal(label({ dataset: config.data.datasets[0], dataIndex: 0, parsed: { y: 6.5 } }), "6h 30min (4)");
});

test("toConfig colours the cells of the heat map by their share of the most", () => {
  const config = charts.toConfig({
    type: "matrix", labels: ["00:00", "01:00"], rows: ["Mon"], ink: "#000", heat: ["#000000", "#ffffff"],
    datasets: [{ label: "n", data: [{ x: "00:00", y: "Mon", v: 0 }, { x: "01:00", y: "Mon", v: 4 }] }],
  });
  const cells = config.data.datasets[0];
  assert.equal(cells.backgroundColor({ dataset: cells, dataIndex: 1 }), "rgb(255, 255, 255)");
  assert.equal(cells.backgroundColor({ dataset: cells, dataIndex: 0 }), "rgb(0, 0, 0)");
  assert.equal(cells.width({ chart: { chartArea: { width: 202 } } }), 100);
  assert.deepEqual(config.options.scales.y.labels, ["Mon"]);
  const label = config.options.plugins.tooltip.callbacks.label;
  assert.equal(label({ dataset: cells, dataIndex: 1 }), "Mon 01:00: 4");
});

function page(theme) {
  return new JSDOM(
    `<html data-bs-theme="${theme}"><body><div><img src="/s/1/chart/hours.svg" alt="Activity by hour" data-chart-json="/s/1/chart/hours.json?login=bob"></div></body></html>`,
    { runScripts: "outside-only", pretendToBeVisual: true },
  );
}

test("setup replaces the image by a canvas of Chart.js, in the theme of the page", async () => {
  const dom = page("dark");
  const img = dom.window.document.querySelector("img");
  const made = [];
  class FakeChart { constructor(canvas, config) { made.push({ canvas, config }); } destroy() { this.gone = true; } }
  const asked = [];
  const state = charts.setup(img, FakeChart, (address) => { asked.push(address); return Promise.resolve(BARS); });
  await state.draw();
  assert.deepEqual(asked, ["/s/1/chart/hours.json?login=bob&theme=dark"]);
  assert.equal(img.hidden, true);
  const canvas = made[0].canvas;
  assert.equal(canvas.tagName, "CANVAS");
  assert.equal(canvas.getAttribute("role"), "img");
  assert.equal(canvas.getAttribute("aria-label"), "Activity by hour");
  assert.equal(img.hasAttribute("data-chart-ready"), true);
  assert.equal(canvas.parentNode.getAttribute("data-chart-theme"), "dark");
  await state.draw();
  assert.equal(dom.window.document.querySelectorAll("canvas").length, 1, "drawn again in place");
});

test("an answer to an older draw is not drawn over a newer one", async () => {
  const dom = page("light");
  const img = dom.window.document.querySelector("img");
  const made = [];
  class FakeChart { constructor(canvas, config) { made.push(config); } destroy() {} }
  const answers = [];
  const state = charts.setup(img, FakeChart, () => new Promise((resolve) => answers.push(resolve)));
  const first = state.draw();
  dom.window.document.documentElement.setAttribute("data-bs-theme", "dark");
  const second = state.draw();
  answers[1]({ ...BARS, ink: "dark ink" });
  await second;
  answers[0]({ ...BARS, ink: "light ink" });
  await first;
  assert.equal(made.length, 1);
  assert.equal(made[0].options.scales.x.ticks.color, "dark ink");
  assert.equal(dom.window.document.querySelector(".chart-canvas").getAttribute("data-chart-theme"), "dark");
});

test("the image stays without data or when the data cannot be read", async () => {
  for (const answer of [Promise.resolve({ ...BARS, empty: true }), Promise.reject(new Error("500"))]) {
    const img = page("light").window.document.querySelector("img");
    const state = charts.setup(img, class {}, () => answer);
    assert.equal(await state.draw(), null);
    assert.equal(img.hidden, false);
  }
});

test("the real Chart.js draws the configuration, also the heat map", () => {
  const dom = page("light");
  const window = dom.window;
  window.HTMLCanvasElement.prototype.getContext = () => null; // jsdom draws nothing
  // the files the pages load
  window.eval(fs.readFileSync(`${__dirname}/../../static/vendor/chartjs/chart.umd.js`, "utf8"));
  window.eval(fs.readFileSync(`${__dirname}/../../static/vendor/chartjs/chartjs-chart-matrix.min.js`, "utf8"));
  const canvas = window.document.createElement("canvas");
  window.document.body.appendChild(canvas);
  const bars = new window.Chart(canvas, charts.toConfig(BARS));
  assert.equal(bars.config.type, "bar");
  assert.ok(window.Chart.registry.getController("matrix"), "chartjs-chart-matrix is registered");
});

test("heatColor hits the middle stop and treats a missing share as none", () => {
  const stops = ["#000000", "#808080", "#ffffff"];
  assert.equal(charts.heatColor(stops, 0.5), "rgb(128, 128, 128)");
  assert.equal(charts.heatColor(stops, undefined), "rgb(0, 0, 0)");
  assert.equal(charts.heatColor(stops, -1), "rgb(0, 0, 0)");
});

test("a heat map of only zeros has the colour of few everywhere", () => {
  const config = charts.toConfig({
    type: "matrix", labels: ["00:00"], rows: ["Mon"], ink: "#000", heat: ["#000000", "#ffffff"],
    datasets: [{ label: "n", data: [{ x: "00:00", y: "Mon", v: 0 }] }],
  });
  const cells = config.data.datasets[0];
  assert.equal(cells.backgroundColor({ dataset: cells, dataIndex: 0 }), "rgb(0, 0, 0)");
  assert.equal(cells.width({ chart: {} }), 0, "before Chart.js knows its area");
});

test("toConfig without titles shows none and copies the series", () => {
  const data = { ...BARS, x: "", y: "", datasets: [{ label: "one", data: [1] }] };
  const config = charts.toConfig(data);
  assert.equal(config.options.scales.x.title.display, false);
  assert.equal(config.options.plugins.legend.display, false, "one series needs no legend");
  config.data.datasets[0].label = "changed";
  assert.equal(data.datasets[0].label, "one", "the data of the server stays");
});

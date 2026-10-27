const { test } = require("node:test");
const assert = require("node:assert/strict");
const progress = require("../../static/js/progress.js");

test("formatDuration uses at most two units", () => {
  assert.equal(progress.formatDuration(10), "< 1min");
  assert.equal(progress.formatDuration(45 * 60), "45min");
  assert.equal(progress.formatDuration(3 * 3600), "3h");
  assert.equal(progress.formatDuration(3 * 3600 + 12 * 60), "3h 12min");
  assert.equal(progress.formatDuration(2 * 86400 + 4 * 3600 + 59), "2d 4h");
  assert.equal(progress.formatDuration(86400), "1d");
});

test("formatDuration of nothing is empty", () => {
  for (const value of [null, undefined, NaN, Infinity]) assert.equal(progress.formatDuration(value), "");
  assert.equal(progress.formatDuration(-5), "< 1min");
});

test("describe a complete scope", () => {
  const shown = progress.describe({ percent: 100, items: 10, total: 10, jobs: [] });
  assert.equal(shown.text, "100% of the data (10 of 10 items)");
  assert.equal(shown.active, false);
});

test("describe asks to read when incomplete and idle", () => {
  const shown = progress.describe({ percent: 40, items: 4, total: null, jobs: [] });
  assert.equal(shown.text, "40% of the data, read from GitHub to complete it");
});

test("describe a running fetch with the time left", () => {
  const shown = progress.describe({
    percent: 12.6, items: 126, total: 1000, seconds_left: 600,
    jobs: [{ status: "running" }, { status: "done" }],
  });
  assert.equal(shown.percent, 13);
  assert.equal(shown.text, "13% of the data (126 of 1000 items), complete in about 10min");
  assert.equal(shown.active, true);
});

test("describe limits the percentage", () => {
  assert.equal(progress.describe({ percent: 140, jobs: [] }).percent, 100);
  assert.equal(progress.describe({ percent: -3, jobs: [] }).percent, 0);
  assert.equal(progress.describe({}).percent, 0);
});

function fakeRoot(attributes) {
  const nodes = {
    bar: { style: {}, attributes: {}, setAttribute(n, v) { this.attributes[n] = v; } },
    text: { textContent: "" },
    jobs: { children: [], set textContent(v) { this.children = []; }, appendChild(c) { this.children.push(c); } },
  };
  return {
    nodes,
    ownerDocument: { createElement: () => ({ textContent: "" }), defaultView: { location: { reloads: 0, reload() { this.reloads += 1; } } } },
    getAttribute: (name) => attributes[name] ?? null,
    querySelector: (selector) => nodes[selector.match(/=(\w+)\]/)[1]],
  };
}

test("render fills bar, text and jobs", () => {
  const root = fakeRoot({});
  progress.render(root, { percent: 50, jobs: [{ repository: "o/r", status: "running", percent: 50, message: "" }] });
  assert.equal(root.nodes.bar.style.width, "50%");
  assert.equal(root.nodes.bar.attributes["aria-valuenow"], "50");
  assert.equal(root.nodes.jobs.children[0].textContent, "o/r: running 50%");
});

test("setup polls while active and reloads when the fetch ends", async () => {
  const root = fakeRoot({ "data-progress-url": "/p.json", "data-progress-active": "true", "data-progress-interval": "10" });
  const answers = [
    { percent: 50, jobs: [{ repository: "o/r", status: "running", percent: 50 }] },
    { percent: 100, jobs: [] },
  ];
  const scheduled = [];
  const poll = progress.setup(root, async () => answers.shift(), (f, ms) => scheduled.push([f, ms]));
  assert.equal(scheduled.length, 1, "polling starts when a fetch is active");
  await poll();
  assert.equal(scheduled.length, 2, "still active: poll again");
  await poll();
  assert.equal(root.ownerDocument.defaultView.location.reloads, 1, "done: show the new statistics");
});

test("setup does not poll when nothing runs, and backs off on errors", async () => {
  const scheduled = [];
  const idle = fakeRoot({ "data-progress-url": "/p.json", "data-progress-active": "false", "data-progress-interval": "10" });
  const poll = progress.setup(idle, () => Promise.reject(new Error("offline")), (f, ms) => scheduled.push(ms));
  assert.equal(scheduled.length, 0);
  await poll();
  assert.deepEqual(scheduled, [20]);
});

test("errors of the site are shown with what to do", () => {
  const shown = progress.describeError({
    error: { title: "Unexpected error", detail: "KeyError: x", docs_url: "https://docs/errors#x" },
  });
  assert.equal(shown.text, "Unexpected error: KeyError: x");
  assert.equal(shown.link, "https://docs/errors#x");
});

test("a site that cannot be reached is said so", () => {
  for (const answer of [null, undefined, new Error("offline"), {}]) {
    const shown = progress.describeError(answer);
    assert.match(shown.text, /cannot be reached/);
    assert.equal(shown.link, null);
  }
});

test("renderError adds the link", () => {
  const appended = [];
  const text = { textContent: "", appendChild: (child) => appended.push(child) };
  const root = {
    ownerDocument: { createElement: () => ({}) },
    querySelector: () => text,
  };
  progress.renderError(root, { error: { title: "T", detail: "D", docs_url: "u" } });
  assert.equal(text.textContent, "T: D ");
  assert.equal(appended[0].href, "u");
  assert.equal(appended[0].textContent, "What to do");
});

test("setup shows an error and polls again later", async () => {
  const text = { textContent: "", appendChild() {} };
  const root = {
    ownerDocument: { createElement: () => ({}), defaultView: null },
    getAttribute: (n) => ({ "data-progress-url": "/p", "data-progress-active": "true", "data-progress-interval": "10" })[n] ?? null,
    querySelector: () => text,
  };
  const scheduled = [];
  const poll = progress.setup(root, () => Promise.reject({ error: { title: "T", detail: "D" } }), (f, ms) => scheduled.push(ms));
  await poll();
  assert.equal(text.textContent, "T: D ");
  assert.deepEqual(scheduled, [10, 20]);
});

test("the texts are translated with the catalog of Django when it is there", () => {
  globalThis.gettext = (text) => (text === "%(percent)s% of the data" ? "%(percent)s% der Daten" : text);
  try {
    assert.equal(progress.describe({ percent: 40, jobs: [] }).text, "40% der Daten, read from GitHub to complete it");
  } finally {
    delete globalThis.gettext;
  }
});

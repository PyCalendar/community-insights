const { test } = require("node:test");
const assert = require("node:assert/strict");
const progress = require("../../static/js/document-progress.js");

function page() {
  const inner = { style: {}, textContent: "" };
  const parts = {
    "[data-document-bar]": { attributes: {}, firstElementChild: inner, setAttribute(k, v) { this.attributes[k] = v; } },
    "[data-document-state]": { textContent: "" },
    "[data-document-download]": { hidden: true },
    "[data-document-error]": { hidden: true, textContent: "" },
  };
  return {
    inner,
    parts,
    getAttribute: () => "/documents/1/progress.json",
    querySelector: (selector) => parts[selector] || null,
  };
}

test("waiting while queued or running", () => {
  assert.equal(progress.waiting("queued"), true);
  assert.equal(progress.waiting("running"), true);
  assert.equal(progress.waiting("done"), false);
  assert.equal(progress.waiting("failed"), false);
});

test("show moves the bar and shows the download when it is ready", () => {
  const root = page();
  progress.show(root, { status: "running", progress: 45 });
  assert.equal(root.inner.style.width, "45%");
  assert.equal(root.parts["[data-document-bar]"].attributes["aria-valuenow"], "45");
  assert.equal(root.parts["[data-document-download]"].hidden, true);
  progress.show(root, { status: "done", progress: 100 });
  assert.equal(root.parts["[data-document-download]"].hidden, false);
  assert.equal(root.parts["[data-document-state]"].textContent, "The file is ready.");
  progress.show(root, { status: "running", progress: 250 });
  assert.equal(root.inner.style.width, "100%", "never more than 100");
});

test("show tells what went wrong", () => {
  const root = page();
  progress.show(root, { status: "failed", progress: 30, message: "No such table" });
  assert.equal(root.parts["[data-document-error]"].hidden, false);
  assert.equal(root.parts["[data-document-error]"].textContent, "No such table");
  const other = page();
  progress.show(other, { status: "failed", progress: 0, message: "" });
  assert.equal(other.parts["[data-document-error]"].textContent, "The file could not be made.");
});

test("setup asks until the document is finished, and later again after a failure", async () => {
  const answers = [{ status: "queued", progress: 0 }, { status: "running", progress: 50 }, { status: "done", progress: 100 }];
  const waits = [];
  const root = page();
  let later;
  const pending = [];
  await progress.setup(root, async () => answers.shift(), (f, ms) => { waits.push(ms); pending.push(f); });
  while (pending.length) await pending.shift()();
  assert.deepEqual(waits, [1000, 1000]);
  assert.equal(root.parts["[data-document-download]"].hidden, false);
  const failed = [];
  await progress.setup(page(), async () => { throw new Error("offline"); }, (f, ms) => failed.push(ms));
  assert.deepEqual(failed, [5000]);
});

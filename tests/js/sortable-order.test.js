const { test } = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");
const order = require("../../static/js/sortable-order.js");

function page() {
  return new JSDOM(`
    <form id="class-order" hidden><input type="hidden" name="action" value="order"></form>
    <div data-sort-list data-sort-form="class-order">
      <div data-sort-id="1"><span data-sort-handle>⠿</span></div>
      <div data-sort-id="2"><span data-sort-handle>⠿</span></div>
      <div data-sort-id="3"><span data-sort-handle>⠿</span></div>
    </div>`).window.document;
}

/* Records what Sortable.create was called with. */
function fakeSortable() {
  const calls = [];
  return { calls, create: (element, options) => { calls.push({ element, options }); return calls.at(-1); } };
}

test("ids reads the items from top to bottom", () => {
  assert.deepEqual(order.ids(page().querySelector("[data-sort-list]")), ["1", "2", "3"]);
});

test("fill replaces the order fields of the form", () => {
  const form = page().getElementById("class-order");
  order.fill(form, ["3", "1"]);
  order.fill(form, ["2", "3", "1"]);
  const values = Array.from(form.querySelectorAll('input[name="order"]'), (input) => input.value);
  assert.deepEqual(values, ["2", "3", "1"]);
  assert.equal(form.querySelector('input[name="action"]').value, "order", "other fields stay");
});

test("setup drags the items by their handle", () => {
  const doc = page();
  const Sortable = fakeSortable();
  order.setup(doc.querySelector("[data-sort-list]"), Sortable);
  const { element, options } = Sortable.calls[0];
  assert.equal(element, doc.querySelector("[data-sort-list]"));
  assert.equal(options.handle, "[data-sort-handle]");
  assert.equal(options.draggable, "[data-sort-id]");
});

test("a drop sends the new order", () => {
  const doc = page();
  const list = doc.querySelector("[data-sort-list]");
  const form = doc.getElementById("class-order");
  let sent = 0;
  form.submit = () => { sent += 1; };
  const Sortable = fakeSortable();
  order.setup(list, Sortable);
  list.appendChild(list.firstElementChild); // what Sortable did: 1 is now last
  Sortable.calls[0].options.onEnd({ oldIndex: 0, newIndex: 2 });
  assert.equal(sent, 1);
  assert.deepEqual(Array.from(form.querySelectorAll('input[name="order"]'), (i) => i.value), ["2", "3", "1"]);
});

test("a drop at the same place sends nothing", () => {
  const doc = page();
  const form = doc.getElementById("class-order");
  let sent = 0;
  form.submit = () => { sent += 1; };
  const Sortable = fakeSortable();
  order.setup(doc.querySelector("[data-sort-list]"), Sortable);
  Sortable.calls[0].options.onEnd({ oldIndex: 1, newIndex: 1 });
  assert.equal(sent, 0);
});

test("without the form or Sortable.js nothing is set up", () => {
  const doc = page();
  const list = doc.querySelector("[data-sort-list]");
  assert.equal(order.setup(list, undefined), null, "Sortable.js did not load");
  list.setAttribute("data-sort-form", "missing");
  assert.equal(order.setup(list, fakeSortable()), null, "no form of that id");
});

test("the real Sortable.js accepts the options", () => {
  const dom = new JSDOM(page().documentElement.outerHTML, { runScripts: "outside-only" });
  const source = require("node:fs").readFileSync(require.resolve("sortablejs/Sortable.min.js"), "utf8");
  dom.window.eval(source);
  const sortable = order.setup(dom.window.document.querySelector("[data-sort-list]"), dom.window.Sortable);
  assert.ok(sortable instanceof dom.window.Sortable);
  assert.equal(sortable.option("handle"), "[data-sort-handle]");
});

test("an empty list has no ids and an empty order removes the old one", () => {
  const doc = new JSDOM('<form id="f"><input name="order" value="1"></form><div data-sort-list data-sort-form="f"></div>').window.document;
  assert.deepEqual(order.ids(doc.querySelector("[data-sort-list]")), []);
  order.fill(doc.getElementById("f"), []);
  assert.equal(doc.querySelectorAll('input[name="order"]').length, 0);
});

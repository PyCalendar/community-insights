const { test } = require("node:test");
const assert = require("node:assert/strict");
const columns = require("../../static/js/columns.js");

const DEFAULTS = ["login", "class", "comments"];

test("parse reads spaces and commas and falls back to the defaults", () => {
  assert.deepEqual(columns.parse("login  reviews,comments", DEFAULTS), ["login", "reviews", "comments"]);
  assert.deepEqual(columns.parse("", DEFAULTS), DEFAULTS);
  assert.deepEqual(columns.parse(undefined, DEFAULTS), DEFAULTS);
  const parsed = columns.parse("", DEFAULTS);
  parsed.push("x");
  assert.deepEqual(DEFAULTS, ["login", "class", "comments"], "the defaults are not changed");
});

test("serialize keeps the defaults empty", () => {
  assert.equal(columns.serialize(DEFAULTS.slice(), DEFAULTS), "");
  assert.equal(columns.serialize(["class", "login", "comments"], DEFAULTS), "class login comments");
  assert.equal(columns.serialize([], DEFAULTS), "");
});

test("move stays in the list", () => {
  assert.deepEqual(columns.move(["a", "b", "c"], 0, 1), ["b", "a", "c"]);
  assert.deepEqual(columns.move(["a", "b", "c"], 2, -1), ["a", "c", "b"]);
  assert.deepEqual(columns.move(["a", "b", "c"], 0, -1), ["a", "b", "c"]);
  assert.deepEqual(columns.move(["a", "b", "c"], 2, 5), ["a", "b", "c"]);
});

test("moveTo drops a column at the place of another", () => {
  assert.deepEqual(columns.moveTo(["a", "b", "c", "d"], 0, 2), ["b", "c", "a", "d"]);
  assert.deepEqual(columns.moveTo(["a", "b", "c", "d"], 3, 0), ["d", "a", "b", "c"]);
});

test("remove and add", () => {
  assert.deepEqual(columns.remove(["a", "b", "c"], 1), ["a", "c"]);
  assert.deepEqual(columns.add(["a"], "b"), ["a", "b"]);
  assert.deepEqual(columns.add(["a", "b"], "a"), ["a", "b"], "only once");
  assert.deepEqual(columns.add(["a"], ""), ["a"]);
});

test("setup draws the columns and moves them when Sortable.js drops one", () => {
  const { JSDOM } = require("jsdom");
  const doc = new JSDOM(
    '<form><input data-columns-input data-columns-default="a b c" data-columns-names="a b c d" value=""></form>',
  ).window.document;
  const input = doc.querySelector("input");
  const calls = [];
  const Sortable = { create: (element, options) => calls.push({ element, options }) };
  const editor = columns.setup(input, Sortable);
  assert.equal(input.hidden, true);
  assert.deepEqual(Array.from(editor.list.children, (li) => li.getAttribute("data-column")), ["a", "b", "c"]);
  assert.equal(calls[0].element, editor.list);
  assert.equal(calls[0].options.filter, "button", "the buttons stay clickable");
  calls[0].options.onEnd({ oldIndex: 0, newIndex: 2 });
  assert.equal(input.value, "b c a");
  assert.deepEqual(Array.from(editor.list.children, (li) => li.getAttribute("data-column")), ["b", "c", "a"]);
  calls[0].options.onEnd({ oldIndex: 1, newIndex: 1 });
  assert.equal(input.value, "b c a", "a drop at the same place changes nothing");
});

test("setup works without Sortable.js: the arrow buttons still move", () => {
  const { JSDOM } = require("jsdom");
  const doc = new JSDOM(
    '<form><input data-columns-input data-columns-default="a b" data-columns-names="a b" value=""></form>',
  ).window.document;
  const input = doc.querySelector("input");
  const editor = columns.setup(input, undefined);
  editor.list.querySelector('[data-column="a"] [data-column-action="right"]').click();
  assert.equal(input.value, "b a");
});

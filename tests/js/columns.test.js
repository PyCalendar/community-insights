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

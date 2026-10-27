const { test } = require("node:test");
const assert = require("node:assert/strict");
const order = require("../../static/js/classes-order.js");

test("reorder puts the dragged class at the place of the target", () => {
  assert.deepEqual(order.reorder(["1", "2", "3", "4"], "1", "3"), ["2", "3", "1", "4"]);
  assert.deepEqual(order.reorder(["1", "2", "3", "4"], "4", "1"), ["4", "1", "2", "3"]);
  assert.deepEqual(order.reorder(["1", "2"], "2", "2"), ["1", "2"]);
  assert.deepEqual(order.reorder(["1", "2"], "9", "1"), ["1", "2"], "unknown ids change nothing");
});

test("fill replaces the order fields of the form", () => {
  const children = [];
  const form = {
    ownerDocument: { createElement: () => ({}) },
    appendChild: (child) => children.push(child),
    querySelectorAll: () => children.slice().map((child) => ({
      ...child,
      parentNode: { removeChild: () => children.splice(children.indexOf(child), 1) },
    })),
  };
  order.fill(form, ["3", "1"]);
  assert.deepEqual(children.map((c) => [c.name, c.value, c.type]), [["order", "3", "hidden"], ["order", "1", "hidden"]]);
  order.fill(form, ["1"]);
  assert.deepEqual(children.map((c) => c.value), ["1"]);
});

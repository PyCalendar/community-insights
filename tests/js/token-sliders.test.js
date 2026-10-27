const { test } = require("node:test");
const assert = require("node:assert/strict");
const sliders = require("../../static/js/token-sliders.js");

test("the default: all points, 10 % of them shared = 500", () => {
  assert.deepEqual(sliders.points(5000, 100, 10), { max: 5000, shared: 500, reserve: 0, own: 4500 });
});

test("the share moves with the maximum", () => {
  assert.equal(sliders.points(5000, 50, 10).shared, 250);
  assert.equal(sliders.points(5000, 0, 10).shared, 0);
  assert.equal(sliders.points(5000, 50, 100).shared, 2500);
});

test("the share is never more than the maximum", () => {
  for (const max of [0, 1, 33, 50, 99, 100]) {
    for (const shared of [0, 10, 50, 100]) {
      const p = sliders.points(5000, max, shared);
      assert.ok(p.shared <= p.max, `${max} ${shared}`);
      assert.equal(p.max + p.reserve, 5000);
    }
  }
});

test("percentages are limited to 0-100 and whole", () => {
  assert.equal(sliders.clamp(150), 100);
  assert.equal(sliders.clamp(-5), 0);
  assert.equal(sliders.clamp("33.6"), 34);
  assert.equal(sliders.clamp("abc"), 0);
});

test("other limits than 5000", () => {
  assert.deepEqual(sliders.points(15000, 10, 50), { max: 1500, shared: 750, reserve: 13500, own: 750 });
});

test("describe says it in words", () => {
  const text = sliders.describe(5000, 90, 10);
  assert.equal(text.max, "4500 of 5000 points per hour, stopping when 500 are left");
  assert.equal(text.shared, "450 of 4500 points per hour for others on this site");
});

test("setup follows the sliders", () => {
  const listeners = [];
  const parts = {
    max: { value: "100", addEventListener: (t, f) => listeners.push(f) },
    shared: { value: "10", addEventListener: (t, f) => listeners.push(f) },
  };
  const texts = { max: { textContent: "" }, shared: { textContent: "" } };
  const root = {
    getAttribute: () => "5000",
    querySelector: (s) => (s.startsWith("[data-slider=") ? parts[s.match(/=(\w+)\]/)[1]] : texts[s.match(/=(\w+)\]/)[1]]),
  };
  sliders.setup(root);
  assert.match(texts.shared.textContent, /^500 of 5000/);
  parts.max.value = "50";
  listeners[0]();
  assert.match(texts.max.textContent, /^2500 of 5000/);
  assert.match(texts.shared.textContent, /^250 of 2500/);
});

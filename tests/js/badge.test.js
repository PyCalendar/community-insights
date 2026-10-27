const { test } = require("node:test");
const assert = require("node:assert/strict");
const badge = require("../../static/js/badge.js");

const BASE = "https://example.org/badge/TOKEN.svg";

test("badgeUrl builds the query", () => {
  assert.equal(badge.badgeUrl(BASE, "pr", "95", ""), BASE + "?kind=pr&percentile=95");
  assert.equal(badge.badgeUrl(BASE, "issue", 50, "bot"), BASE + "?kind=issue&percentile=50&class=bot");
});

test("badgeUrl encodes class names", () => {
  assert.equal(
    badge.badgeUrl(BASE, "pr", 50, "collaborator or higher"),
    BASE + "?kind=pr&percentile=50&class=collaborator%20or%20higher",
  );
  assert.match(badge.badgeUrl(BASE, "pr", 50, "a&b=c#d"), /class=a%26b%3Dc%23d$/);
});

test("badgeUrl limits the percentile and the kind", () => {
  assert.match(badge.badgeUrl(BASE, "pr", 150, ""), /percentile=100$/);
  assert.match(badge.badgeUrl(BASE, "pr", -3, ""), /percentile=0$/);
  assert.match(badge.badgeUrl(BASE, "pr", "abc", ""), /percentile=50$/);
  assert.match(badge.badgeUrl(BASE, "anything", 50, ""), /kind=pr/);
});

test("markdown names the kind", () => {
  assert.equal(badge.markdown("u", "issue"), "![issue response time](u)");
  assert.equal(badge.markdown("u", "pr"), "![pull request response time](u)");
});

function element(value) {
  return {
    value,
    attributes: {},
    listeners: [],
    setAttribute(name, v) { this.attributes[name] = v; },
    addEventListener(type, f) { this.listeners.push(f); },
  };
}

test("setup fills preview and markdown and follows changes", () => {
  const parts = {
    kind: element("pr"), percentile: element("95"), class: element(""),
    preview: element(), markdown: element(""),
  };
  const root = {
    getAttribute: () => BASE,
    querySelector: (selector) => parts[selector.match(/"(.*)"/)[1]],
  };
  badge.setup(root);
  assert.equal(parts.preview.attributes.src, BASE + "?kind=pr&percentile=95");
  parts.kind.value = "issue";
  parts.class.value = "bot";
  parts.kind.listeners[0]();
  assert.equal(parts.preview.attributes.src, BASE + "?kind=issue&percentile=95&class=bot");
  assert.match(parts.markdown.value, /^!\[issue response time\]/);
});

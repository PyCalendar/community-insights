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

test("badgeUrl adds the left side when it is given", () => {
  assert.equal(badge.badgeUrl(BASE, "pr", 95, "", "  "), BASE + "?kind=pr&percentile=95");
  assert.equal(
    badge.badgeUrl(BASE, "pr", 95, "", " time to answer "),
    BASE + "?kind=pr&percentile=95&label=time%20to%20answer",
  );
  assert.match(badge.badgeUrl(BASE, "pr", 95, "", "a&b"), /label=a%26b$/);
});

test("badgeUrl names the model unless it is the measured one", () => {
  assert.equal(badge.badgeUrl(BASE, "pr", 95, "", "", "measured"), BASE + "?kind=pr&percentile=95");
  assert.equal(badge.badgeUrl(BASE, "pr", 95, "", "", ""), BASE + "?kind=pr&percentile=95");
  assert.equal(
    badge.badgeUrl(BASE, "pr", 95, "bot", "x", "kaplan-meier"),
    BASE + "?kind=pr&percentile=95&class=bot&model=kaplan-meier&label=x",
  );
});

test("setup follows the choice of the model", () => {
  const parts = {
    kind: element("pr"), percentile: element("95"), class: element(""), preview: element(),
    model: element("measured"),
  };
  const root = element();
  root.attributes["data-badge-url"] = BASE;
  root.querySelector = (selector) => parts[selector.match(/"(.*)"/)[1]];
  badge.setup(root, undefined);
  parts.model.value = "exponential";
  parts.model.listeners[0]();
  assert.equal(parts.preview.attributes.src, BASE + "?kind=pr&percentile=95&model=exponential");
});

test("altText is the left side or names the kind", () => {
  assert.equal(badge.altText("issue", ""), "issue response time");
  assert.equal(badge.altText("pr", undefined), "pull request response time");
  assert.equal(badge.altText("pr", " answers "), "answers");
});

function element(value) {
  return {
    value,
    attributes: {},
    listeners: [],
    setAttribute(name, v) { this.attributes[name] = v; },
    getAttribute(name) { return this.attributes[name]; },
    addEventListener(type, f) { this.listeners.push(f); },
  };
}

function builder(withLabel) {
  const parts = {
    kind: element("pr"), percentile: element("95"), class: element(""), preview: element(),
  };
  if (withLabel) parts.label = element("");
  const root = element();
  root.attributes["data-badge-url"] = BASE;
  root.querySelector = (selector) => parts[selector.match(/"(.*)"/)[1]];
  return { parts, root };
}

test("setup fills the preview and the code to share and follows changes", () => {
  const { parts, root } = builder(true);
  const filled = [];
  badge.setup(root, { fill: (r, url) => filled.push([r, url, r.attributes["data-share-alt"]]) });
  assert.equal(parts.preview.attributes.src, BASE + "?kind=pr&percentile=95");
  assert.deepEqual(filled[0], [root, BASE + "?kind=pr&percentile=95", "pull request response time"]);
  parts.kind.value = "issue";
  parts.class.value = "bot";
  parts.kind.listeners[0]();
  assert.equal(parts.preview.attributes.src, BASE + "?kind=issue&percentile=95&class=bot");
  parts.label.value = "answers";
  parts.label.listeners[0]();
  assert.equal(filled.at(-1)[1], BASE + "?kind=issue&percentile=95&class=bot&label=answers");
  assert.equal(filled.at(-1)[2], "answers");
});

test("setup works without the field of the left side and without share.js", () => {
  const { parts, root } = builder(false);
  const update = badge.setup(root, undefined);
  assert.equal(update(), BASE + "?kind=pr&percentile=95");
  assert.equal(parts.preview.attributes.src, BASE + "?kind=pr&percentile=95");
});


test("badgeUrl keeps the classes of the page in the base", () => {
  assert.equal(
    badge.badgeUrl(BASE + "?classes=maintainer-3", "pr", 50, "", "", ""),
    BASE + "?classes=maintainer-3&kind=pr&percentile=50",
  );
});

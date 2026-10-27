const { test } = require("node:test");
const assert = require("node:assert/strict");
const theme = require("../../static/js/theme.js");

test("readChoice reads the cookie, auto otherwise", () => {
  assert.equal(theme.readChoice("a=1; theme=dark"), "dark");
  assert.equal(theme.readChoice("theme=light"), "light");
  assert.equal(theme.readChoice("theme=purple"), "auto");
  assert.equal(theme.readChoice("mytheme=dark"), "auto");
  assert.equal(theme.readChoice(""), "auto");
  assert.equal(theme.readChoice(undefined), "auto");
});

test("resolve: an explicit choice wins over the system", () => {
  assert.equal(theme.resolve("light", true), "light");
  assert.equal(theme.resolve("dark", false), "dark");
  assert.equal(theme.resolve("auto", true), "dark");
  assert.equal(theme.resolve("auto", false), "light");
});

test("chartUrl sets the theme and keeps other parameters", () => {
  assert.equal(theme.chartUrl("/c.svg", "dark"), "/c.svg?theme=dark");
  assert.equal(theme.chartUrl("/c.svg?login=bob", "dark"), "/c.svg?login=bob&theme=dark");
  assert.equal(theme.chartUrl("/c.svg?theme=light", "dark"), "/c.svg?theme=dark");
  assert.equal(theme.chartUrl("/c.svg?theme=light&login=bob", "dark"), "/c.svg?login=bob&theme=dark");
  assert.equal(theme.chartUrl("/c.svg?login=bob&theme=light", "light"), "/c.svg?login=bob&theme=light");
});

function fakeDocument(images, buttons, icons = []) {
  const attributes = {};
  return {
    cookie: "",
    documentElement: { setAttribute: (n, v) => { attributes[n] = v; } },
    attributes,
    querySelectorAll: (selector) => {
      if (selector.startsWith("img")) return images;
      if (selector === "[data-theme-icon]") return icons;
      return buttons;
    },
  };
}

function element(attrs) {
  return {
    attrs: { ...attrs },
    classes: new Set(),
    getAttribute(n) { return this.attrs[n] ?? null; },
    setAttribute(n, v) { this.attrs[n] = v; },
    classList: { toggle(name, on) { on ? this.owner.classes.add(name) : this.owner.classes.delete(name); } },
  };
}

test("apply sets the page and switches every chart", () => {
  const chart = element({ "data-chart-src": "/c.svg?login=bob", src: "/c.svg?login=bob&theme=light" });
  const dark = element({ "data-theme-set": "dark" });
  dark.classList.owner = dark;
  const auto = element({ "data-theme-set": "auto" });
  auto.classList.owner = auto;
  const doc = fakeDocument([chart], [dark, auto]);
  assert.equal(theme.apply(doc, "dark", false), "dark");
  assert.equal(doc.attributes["data-theme"], "dark");
  assert.equal(doc.attributes["data-bs-theme"], "dark");
  assert.equal(chart.attrs.src, "/c.svg?login=bob&theme=dark");
  assert.equal(dark.attrs["aria-pressed"], "true");
  assert.equal(auto.attrs["aria-pressed"], "false");
  assert.ok(dark.classes.has("active"));
});

test("apply shows the icon of the choice on the button of the switch", () => {
  const icon = { textContent: "" };
  const doc = fakeDocument([], [], [icon]);
  theme.apply(doc, "dark", false);
  assert.equal(icon.textContent, theme.ICONS.dark);
  theme.apply(doc, "light", true);
  assert.equal(icon.textContent, theme.ICONS.light);
  theme.apply(doc, "auto", true);
  assert.equal(icon.textContent, theme.ICONS.auto, "auto keeps its icon, also when the page is dark");
  assert.notEqual(theme.ICONS.light, theme.ICONS.dark);
});

test("setup follows the system in auto and stores a choice", () => {
  const listeners = {};
  const media = { matches: true, addEventListener: (type, f) => { listeners.media = f; } };
  const doc = fakeDocument([], []);
  doc.addEventListener = (type, f) => { listeners[type] = f; };
  const choose = theme.setup({ document: doc, matchMedia: () => media });
  assert.equal(doc.attributes["data-theme"], "dark", "auto and the system is dark");
  media.matches = false;
  listeners.media();
  assert.equal(doc.attributes["data-theme"], "light", "the system changed");
  choose("dark");
  assert.match(doc.cookie, /^theme=dark;/);
  assert.equal(doc.attributes["data-theme"], "dark");
});

test("setup works without matchMedia", () => {
  const doc = fakeDocument([], []);
  doc.addEventListener = () => {};
  theme.setup({ document: doc });
  assert.equal(doc.attributes["data-theme"], "light");
});

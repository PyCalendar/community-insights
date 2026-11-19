const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");
const map = require("../../static/js/country-map.js");

const WORLD = { x: 0, y: 0, w: 1000, h: 500 };

test("parseHash reads the country of the address", () => {
  assert.equal(map.parseHash("#country=DE"), "DE");
  assert.equal(map.parseHash("#country=at"), "AT");
  assert.equal(map.parseHash("#x=1&country=FR"), "FR");
  assert.equal(map.parseHash("#country=DEU"), null);
  assert.equal(map.parseHash(""), null);
  assert.equal(map.parseHash(undefined), null);
});

test("pick prefers a small country near the pointer over the one under it", () => {
  const countries = [
    { code: "IT", x: 530, y: 100, small: false },
    { code: "VA", x: 531, y: 101, small: true },
    { code: "SM", x: 535, y: 95, small: true },
  ];
  assert.equal(map.pick("IT", { x: 531.5, y: 101.5 }, countries, 3), "VA", "nearest small one");
  assert.equal(map.pick("IT", { x: 534, y: 96 }, countries, 3), "SM");
  assert.equal(map.pick("IT", { x: 520, y: 120 }, countries, 3), "IT", "too far from small ones");
  assert.equal(map.pick(null, { x: 0, y: 0 }, countries, 3), null, "the sea");
  assert.equal(map.pick(null, { x: 531, y: 101 }, countries, 3), "VA", "a dot in the sea");
});

test("zoom keeps the point under the pointer and stays in the map", () => {
  const view = map.zoom(WORLD, 0.5, { x: 250, y: 250 }, WORLD);
  assert.deepEqual(view, { x: 125, y: 125, w: 500, h: 250 });
  const out = map.zoom(view, 10, { x: 250, y: 250 }, WORLD);
  assert.deepEqual(out, WORLD, "never more than the whole world");
  const deep = map.zoom(WORLD, 0.0001, { x: 500, y: 250 }, WORLD);
  assert.equal(deep.w, 1000 / 40, "at most 40 times");
});

test("clamp moves the view back into the map", () => {
  assert.deepEqual(map.clamp({ x: -50, y: 400, w: 500, h: 250 }, WORLD), { x: 0, y: 250, w: 500, h: 250 });
});

test("tipOf uses the tip of the list or says nobody is from there", () => {
  const tips = { DE: "3 contributors from Germany" };
  assert.equal(map.tipOf("DE", tips, {}, "No contributors from {country}"), "3 contributors from Germany");
  assert.equal(map.tipOf("FR", tips, { FR: "France" }, "No contributors from {country}"), "No contributors from France");
  assert.equal(map.tipOf("XX", tips, {}, "No contributors from {country}"), "No contributors from XX");
});

function page(hash) {
  const svg = fs.readFileSync(path.join(__dirname, "../../static/maps/world.svg"), "utf8");
  const dom = new JSDOM(`<!doctype html><body>
    <div data-world-map data-src="/world.svg" data-places='[[522,66,"Berlin, Germany: 2 contributors"]]'
      data-names='{"FR":"France","DE":"Germany","VA":"Vatican City"}' data-nobody="No contributors from {country}">
      <button data-zoom="in"></button><button data-zoom="reset"></button><div data-map-tip hidden></div></div>
    <ol data-country-list>
      <li data-country="DE" data-heat="5" data-tip="2 contributors from Germany"></li>
      <li data-country="VA" data-heat="1" data-tip="1 contributor from Vatican City"></li>
    </ol>
    <p data-choose-country hidden>Choose</p>
    <section data-country-detail="DE"></section><section data-country-detail="VA"></section>
  </body>`, { url: "https://example.org/s/o~r/countries/" + (hash || "") });
  const win = dom.window;
  win.fetch = () => Promise.resolve({ text: () => Promise.resolve(svg) });
  win.SVGElement.prototype.getBoundingClientRect = () => ({ left: 0, top: 0, width: 1000, height: 439.3 });
  return win;
}

async function loaded(win) {
  map.setup(win.document, win);
  for (let i = 0; i < 5; i++) await new Promise((resolve) => setTimeout(resolve, 0));
  return win.document.querySelector("svg");
}

test("the map colours the countries of the list and leaves the others gray", async () => {
  const win = page();
  const svg = await loaded(win);
  const doc = win.document;
  assert.ok(doc.querySelector('path[data-country="DE"]').classList.contains("heat-5"));
  assert.equal(doc.querySelector('path[data-country="FR"]').getAttribute("class"), null);
  assert.equal(svg.getAttribute("role"), "img");
  assert.equal(doc.querySelectorAll("circle.place").length, 1, "the dot of Berlin");
  assert.ok(doc.querySelector("circle.small-country.heat-1"), "the Vatican gets a dot to be seen");
  assert.equal(doc.querySelector("[data-choose-country]").hidden, false, "no country chosen yet");
  assert.ok([...doc.querySelectorAll("[data-country-detail]")].every((s) => s.hidden));
});

test("the address chooses the country shown below the map", async () => {
  const win = page("#country=DE");
  await loaded(win);
  const doc = win.document;
  assert.equal(doc.querySelector('[data-country-detail="DE"]').hidden, false);
  assert.equal(doc.querySelector('[data-country-detail="VA"]').hidden, true);
  assert.ok(doc.querySelector('path[data-country="DE"]').classList.contains("chosen"));
  win.location.hash = "country=FR";
  win.dispatchEvent(new win.HashChangeEvent("hashchange"));
  assert.equal(doc.querySelector("[data-choose-country]").textContent, "No contributors from France");
});

test("a click on a country opens its address; the tool tip names it", async () => {
  const win = page();
  const svg = await loaded(win);
  const doc = win.document;
  const germany = doc.querySelector('path[data-country="DE"]');
  const at = { clientX: 524, clientY: 63, pointerId: 1, bubbles: true };
  germany.dispatchEvent(new win.MouseEvent("pointermove", at));
  assert.equal(doc.querySelector("[data-map-tip]").textContent, "2 contributors from Germany");
  assert.equal(doc.querySelector("[data-map-tip]").hidden, false);
  germany.dispatchEvent(new win.MouseEvent("pointerdown", at));
  germany.dispatchEvent(new win.MouseEvent("pointerup", at));
  assert.equal(win.location.hash, "#country=DE");
  assert.ok(svg);
});

test("the small Vatican is chosen near its centre, on top of Italy", async () => {
  const win = page();
  await loaded(win);
  const doc = win.document;
  const vatican = doc.querySelector('path[data-country="VA"]');
  const x = Number(vatican.getAttribute("data-x")), y = Number(vatican.getAttribute("data-y"));
  const italy = doc.querySelector('path[data-country="IT"]');
  const at = { clientX: x + 3, clientY: y + 3, pointerId: 1, bubbles: true };
  italy.dispatchEvent(new win.MouseEvent("pointerdown", at));
  italy.dispatchEvent(new win.MouseEvent("pointerup", at));
  assert.equal(win.location.hash, "#country=VA");
});

test("the zoom buttons change the view box, reset shows the whole world", async () => {
  const win = page();
  const svg = await loaded(win);
  const whole = svg.getAttribute("viewBox");
  win.document.querySelector('[data-zoom="in"]').dispatchEvent(new win.MouseEvent("click"));
  const zoomed = svg.getAttribute("viewBox").split(" ").map(Number);
  assert.equal(Math.round(zoomed[2]), 600);
  win.document.querySelector('[data-zoom="reset"]').dispatchEvent(new win.MouseEvent("click"));
  assert.equal(svg.getAttribute("viewBox"), whole);
});

test("dragging moves the map instead of choosing a country", async () => {
  const win = page();
  const svg = await loaded(win);
  win.document.querySelector('[data-zoom="in"]').dispatchEvent(new win.MouseEvent("click"));
  const before = svg.getAttribute("viewBox");
  const germany = win.document.querySelector('path[data-country="DE"]');
  germany.dispatchEvent(new win.MouseEvent("pointerdown", { clientX: 500, clientY: 200, pointerId: 1, bubbles: true }));
  germany.dispatchEvent(new win.MouseEvent("pointermove", { clientX: 450, clientY: 200, pointerId: 1, bubbles: true }));
  germany.dispatchEvent(new win.MouseEvent("pointerup", { clientX: 450, clientY: 200, pointerId: 1, bubbles: true }));
  assert.notEqual(svg.getAttribute("viewBox"), before);
  assert.equal(win.location.hash, "", "no country chosen by a drag");
});

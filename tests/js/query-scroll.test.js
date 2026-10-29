const { test } = require("node:test");
const assert = require("node:assert/strict");
const scroll = require("../../static/js/query-scroll.js");

function form() {
  const { JSDOM } = require("jsdom");
  const doc = new JSDOM('<form data-scroll-on-submit><input name="where"></form>').window.document;
  const element = doc.querySelector("form");
  const scrolled = [];
  element.scrollIntoView = (options) => scrolled.push(options);
  scroll.setup(element);
  element.dispatchEvent(new doc.defaultView.Event("submit", { cancelable: true }));
  return scrolled;
}

test("running the query scrolls it to the top of the window", () => {
  assert.deepEqual(form(), [{ block: "start", behavior: "smooth" }]);
});

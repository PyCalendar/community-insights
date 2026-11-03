const { test } = require("node:test");
const assert = require("node:assert/strict");
const submit = require("../../static/js/submit-on-change.js");

test("choosing another option sends the form", () => {
  const { JSDOM } = require("jsdom");
  const doc = new JSDOM(
    '<form><select name="language" data-submit-on-change><option value="en">English</option><option value="de">Deutsch</option></select></form>'
  ).window.document;
  const select = doc.querySelector("select");
  let sent = 0;
  select.form.requestSubmit = () => { sent += 1; };
  submit.setup(select);
  select.value = "de";
  select.dispatchEvent(new doc.defaultView.Event("change"));
  assert.equal(sent, 1);
});

test("a select without a form does nothing", () => {
  const { JSDOM } = require("jsdom");
  const doc = new JSDOM('<select data-submit-on-change><option>a</option></select>').window.document;
  const select = doc.querySelector("select");
  submit.setup(select);
  select.dispatchEvent(new doc.defaultView.Event("change"));
});

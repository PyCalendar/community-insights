const { test } = require("node:test");
const assert = require("node:assert/strict");
const confirm = require("../../static/js/confirm.js");

function element(question) {
  return { getAttribute: (name) => (name === "data-confirm" ? question : null) };
}

test("allowed without a question", () => {
  let asked = false;
  assert.equal(confirm.allowed(element(null), () => { asked = true; }), true);
  assert.equal(asked, false);
});

test("allowed asks the question and follows the answer", () => {
  const questions = [];
  assert.equal(confirm.allowed(element("Delete?"), (q) => { questions.push(q); return true; }), true);
  assert.equal(confirm.allowed(element("Delete?"), () => false), false);
  assert.deepEqual(questions, ["Delete?"]);
});

test("setup stops submitting and clicking when the answer is no", () => {
  const listeners = {};
  const doc = { addEventListener: (name, f) => { listeners[name] = f; } };
  confirm.setup(doc, () => false);
  let prevented = 0;
  listeners.submit({ target: element("Remove?"), preventDefault: () => { prevented++; } });
  const button = element("Delete?");
  listeners.click({ target: { closest: () => button }, preventDefault: () => { prevented++; } });
  listeners.click({ target: { closest: () => null }, preventDefault: () => { prevented++; } });
  assert.equal(prevented, 2);
});

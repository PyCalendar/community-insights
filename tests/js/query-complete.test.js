const { test } = require("node:test");
const assert = require("node:assert/strict");
const complete = require("../../static/js/query-complete.js");

const WORDS = ["prs_total", "prs_merged", "comments_total", "user_class", "and", "or", "not", "in"];

test("wordAt finds the word before the cursor and where it ends", () => {
  assert.deepEqual(complete.wordAt("prs_me >= 2", 6), { start: 0, end: 6, word: "prs_me" });
  assert.deepEqual(complete.wordAt("not cla", 7), { start: 4, end: 7, word: "cla" });
  assert.deepEqual(complete.wordAt("prs_merged", 3), { start: 0, end: 10, word: "prs" });
  assert.deepEqual(complete.wordAt("x >= 2", 6), { start: 6, end: 6, word: "" });
  assert.deepEqual(complete.wordAt("", 0), { start: 0, end: 0, word: "" });
});

test("suggestions start with the word, in any case, and leave out the word itself", () => {
  assert.deepEqual(complete.suggestions(WORDS, "prs"), ["prs_total", "prs_merged"]);
  assert.deepEqual(complete.suggestions(WORDS, "PRS_M"), ["prs_merged"]);
  assert.deepEqual(complete.suggestions(WORDS, "user_class"), []);
  assert.deepEqual(complete.suggestions(WORDS, ""), [], "nothing for no word");
  assert.equal(complete.suggestions(WORDS, "c", 1).length, 1);
});

test("replaceWord puts the word in and a space after it", () => {
  assert.deepEqual(complete.replaceWord("prs_me >= 2", 0, 6, "prs_merged"), { text: "prs_merged >= 2", cursor: 11 });
  assert.deepEqual(complete.replaceWord("not cla", 4, 7, "class"), { text: "not class ", cursor: 10 });
  assert.deepEqual(complete.replaceWord("prs_merged", 0, 10, "prs_total"), { text: "prs_total ", cursor: 10 });
});

test("Enter runs the query unless a suggestion was chosen with the arrows", () => {
  assert.equal(complete.takes("Enter", -1, 3), false, "nothing chosen: the form is sent");
  assert.equal(complete.takes("Enter", 1, 3), true);
  assert.equal(complete.takes("Tab", -1, 3), true, "Tab takes the first one");
  assert.equal(complete.takes("Tab", 2, 3), true);
  assert.equal(complete.takes("Tab", -1, 0), false, "nothing to take");
  assert.equal(complete.takes("a", 0, 3), false);
});

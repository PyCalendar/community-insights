const { test } = require("node:test");
const assert = require("node:assert/strict");
const sources = require("../../static/js/sources.js");

const CHOICES = [
  { name: "plone", kind: "organisation", stars: 0 },
  { name: "plone/volto", kind: "organisation", stars: 500 },
  { name: "plone/plone.restapi", kind: "contributed", stars: 90 },
  { name: "me/tool", kind: "yours", stars: 3 },
  { name: "collective/plone-thing", kind: "contributed", stars: 999 },
  { name: "o/r", kind: "project", stars: 0 },
];

test("asTarget accepts owner and owner/name and GitHub URLs", () => {
  assert.equal(sources.asTarget("a/"), "a");
  assert.equal(sources.asTarget("plone"), "plone");
  assert.equal(sources.asTarget(" plone/volto "), "plone/volto");
  assert.equal(sources.asTarget("https://github.com/plone/volto/"), "plone/volto");
  assert.equal(sources.asTarget("https://github.com/plone/volto.git"), "plone/volto");
  assert.equal(sources.asTarget("a-b/c.d_e"), "a-b/c.d_e");
});

test("asTarget rejects everything else", () => {
  for (const text of ["", " ", "a/b/c", "-x", "x y", "/b", "<b>", "a/b c", null, undefined, "x".repeat(40)]) {
    assert.equal(sources.asTarget(text), null, String(text));
  }
});

test("filter finds parts of names in any case, those starting with the text first", () => {
  const names = sources.filter(CHOICES, "PLONE").map((c) => c.name);
  assert.deepEqual(names.slice(0, 3), ["plone", "plone/volto", "plone/plone.restapi"]);
  assert.ok(names.includes("collective/plone-thing"));
  assert.ok(!names.includes("me/tool"));
});

test("filter without text: projects, own, organisations, contributed; then stars", () => {
  const names = sources.filter(CHOICES, "").map((c) => c.name);
  assert.deepEqual(names, ["o/r", "me/tool", "plone", "plone/volto", "collective/plone-thing", "plone/plone.restapi"]);
});

test("filter limits the number", () => {
  assert.equal(sources.filter(CHOICES, "", 2).length, 2);
  assert.equal(sources.filter([], "x").length, 0);
});

test("offerToAdd only for valid targets that are not listed", () => {
  assert.equal(sources.offerToAdd(CHOICES, "django/django"), "django/django");
  assert.equal(sources.offerToAdd(CHOICES, "PLONE/VOLTO"), null);
  assert.equal(sources.offerToAdd(CHOICES, "not valid!"), null);
  assert.equal(sources.offerToAdd(CHOICES, ""), null);
});

const { test } = require("node:test");
const assert = require("node:assert/strict");
const timeZone = require("../../static/js/time-zone.js");

test("body has the offset and the time zone for django-tz-detect", () => {
  assert.equal(timeZone.body(-60, "Europe/Berlin"), "offset=-60&timezone=Europe%2FBerlin");
  assert.equal(timeZone.body(0, undefined), "offset=0&timezone=");
});

test("send posts to the endpoint of the script with the CSRF header", () => {
  const attributes = {
    "data-endpoint": "/tz_detect/set/",
    "data-csrf-token": "abc",
    "data-csrf-header": "X-CSRFToken",
  };
  const script = { getAttribute: (name) => attributes[name] };
  const sent = [];
  assert.equal(timeZone.send(script, (url, data, headers) => sent.push({ url, data, headers })), true);
  assert.equal(sent[0].url, "/tz_detect/set/");
  assert.match(sent[0].data, /^offset=-?\d+&timezone=/);
  assert.equal(sent[0].headers["X-CSRFToken"], "abc");
});

test("send does nothing without the script", () => {
  assert.equal(timeZone.send(null, () => assert.fail("posted")), false);
});

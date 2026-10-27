const { test } = require("node:test");
const assert = require("node:assert/strict");
const share = require("../../static/js/share.js");

const IMAGE = "https://example.org/badge/T.svg?kind=pr&percentile=95";
const PAGE = "https://example.org/s/o~r/";

test("formats link the image to its page", () => {
  const code = share.formats(IMAGE, PAGE, "PR response");
  assert.equal(code.markdown, `[![PR response](${IMAGE})](${PAGE})`);
  assert.equal(code.rst, `.. image:: ${IMAGE}\n   :alt: PR response\n   :target: ${PAGE}`);
  assert.equal(
    code.html,
    '<a href="https://example.org/s/o~r/"><img src="https://example.org/badge/T.svg?kind=pr&amp;percentile=95" alt="PR response"></a>',
  );
  assert.equal(code.link, IMAGE);
});

test("formats keep the text of the image from breaking the code", () => {
  const code = share.formats("i", "p", 'a [b]\n<c> "d"');
  assert.equal(code.markdown, '[![a  b  <c> "d"](i)](p)');
  assert.match(code.html, /alt="a  b  &lt;c&gt; &quot;d&quot;"/);
  assert.equal(share.formats("i", "p", undefined).markdown, "[![](i)](p)");
});

test("fill writes every field there is and uses a new image", () => {
  const fields = { markdown: { value: "" }, html: { value: "" } };
  const attributes = { "data-share-image": "old", "data-share-link": PAGE, "data-share-alt": "x" };
  const root = {
    getAttribute: (name) => attributes[name],
    querySelector: (selector) => fields[selector.match(/"(.*)"/)[1]] || null,
  };
  share.fill(root);
  assert.equal(fields.markdown.value, `[![x](old)](${PAGE})`);
  share.fill(root, "new");
  assert.equal(fields.markdown.value, `[![x](new)](${PAGE})`);
  assert.match(fields.html.value, /src="new"/);
});

/* Tell the site the time zone of the browser once (django-tz-detect), so times
   are shown in it. The address and the CSRF token are attributes of the script:
   data-endpoint, data-csrf-token and data-csrf-header. */
(function () {
  "use strict";

  /* The form data django-tz-detect reads. */
  function body(offsetMinutes, zone) {
    return "offset=" + encodeURIComponent(offsetMinutes) +
      "&timezone=" + encodeURIComponent(zone || "");
  }

  function send(script, post) {
    if (!script) return false;
    var zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    post(script.getAttribute("data-endpoint"), body(new Date().getTimezoneOffset(), zone), {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Requested-With": "XMLHttpRequest",
      [script.getAttribute("data-csrf-header")]: script.getAttribute("data-csrf-token"),
    });
    return true;
  }

  var api = { body: body, send: send };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else if (navigator.cookieEnabled) {  // without cookies, it is forgotten
    send(document.querySelector("script[data-endpoint][data-csrf-token]"), function (url, data, headers) {
      fetch(url, { method: "POST", body: data, headers: headers, credentials: "same-origin" });
    });
  }
})();

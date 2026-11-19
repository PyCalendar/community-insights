/* The map of the page Countries: the SVG of the world (static/maps/world.svg) is
   loaded into [data-world-map] and coloured by the list of countries
   ([data-country-list] li: data-country, data-heat, data-tip). Pointing at a
   country shows a tool tip; small countries are found within a few pixels of
   their centre, also when the pointer is on a neighbour. A click opens
   #country=XX, which shows that country below the map. The map zooms with the
   wheel, a pinch or the buttons, and moves by dragging. Cities and places of
   contributors are dots (data-places). Without JavaScript, the list and all
   countries are shown. */
(function () {
  "use strict";

  var SVG = "http://www.w3.org/2000/svg";
  var NEAR = 10; /* pixels from the centre of a small country that choose it */
  var SMALL = 12; /* square pixels: a country drawn smaller is small */
  var MOST_ZOOM = 40;
  var DRAG = 4; /* pixels a pointer moves before it drags instead of clicking */

  /* The code of the country of an address part such as "#country=DE", or null. */
  function parseHash(hash) {
    var found = /(?:^#|&)country=([A-Za-z]{2})(?:&|$)/.exec(hash || "");
    return found ? found[1].toUpperCase() : null;
  }

  /* The country to point at: a small country whose centre is within the radius
     (the nearest), else the country under the pointer (or null).
     countries: [{code, x, y, small}], point: {x, y} in units of the map. */
  function pick(under, point, countries, radius) {
    var best = null, distance = radius;
    for (var i = 0; i < countries.length; i++) {
      var c = countries[i];
      if (!c.small) continue;
      var d = Math.hypot(c.x - point.x, c.y - point.y);
      if (d <= distance) { best = c.code; distance = d; }
    }
    return best || under || null;
  }

  /* The view box after zooming by a factor (below 1 zooms in) around a point,
     kept inside the whole map. */
  function zoom(view, factor, center, whole) {
    var w = Math.max(whole.w / MOST_ZOOM, Math.min(whole.w, view.w * factor));
    var h = w * whole.h / whole.w;
    var x = center.x - (center.x - view.x) * (w / view.w);
    var y = center.y - (center.y - view.y) * (h / view.h);
    return clamp({ x: x, y: y, w: w, h: h }, whole);
  }

  /* The view box moved back inside the whole map. */
  function clamp(view, whole) {
    return {
      x: Math.max(whole.x, Math.min(whole.x + whole.w - view.w, view.x)),
      y: Math.max(whole.y, Math.min(whole.y + whole.h - view.h, view.y)),
      w: view.w,
      h: view.h,
    };
  }

  /* The text of a tool tip: that of the list, else "nobody" with the name. */
  function tipOf(code, tips, names, nobody) {
    if (tips[code]) return tips[code];
    return nobody.replace("{country}", names[code] || code);
  }

  function setup(doc, win) {
    var box = doc.querySelector("[data-world-map]");
    if (!box || !win.fetch) return;
    var tip = box.querySelector("[data-map-tip]");
    var heats = {}, tips = {};
    doc.querySelectorAll("[data-country-list] li[data-country]").forEach(function (li) {
      heats[li.getAttribute("data-country")] = li.getAttribute("data-heat");
      tips[li.getAttribute("data-country")] = li.getAttribute("data-tip");
    });
    var names = JSON.parse(box.getAttribute("data-names") || "{}");
    var places = JSON.parse(box.getAttribute("data-places") || "[]");
    var nobody = box.getAttribute("data-nobody") || "{country}";
    var choose = doc.querySelector("[data-choose-country]");
    var details = doc.querySelectorAll("[data-country-detail]");

    win.fetch(box.getAttribute("data-src")).then(function (answer) {
      return answer.text();
    }).then(function (text) {
      box.insertAdjacentHTML("afterbegin", text);
      var svg = box.querySelector("svg");
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", box.getAttribute("data-label") || "");
      start(svg);
    }).catch(function () { /* the list stays */ });

    function start(svg) {
      var parts = svg.getAttribute("viewBox").split(" ").map(Number);
      var whole = { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
      var view = { x: whole.x, y: whole.y, w: whole.w, h: whole.h };
      var countries = [], paths = {}, marks = {};
      var marksGroup = doc.createElementNS(SVG, "g");
      var placesGroup = svg.querySelector("[data-places]");
      svg.querySelector("[data-countries]").after(marksGroup);
      svg.querySelectorAll("path[data-country]").forEach(function (path) {
        var code = path.getAttribute("data-country");
        if (heats[code]) path.classList.add("heat-" + heats[code]);
        paths[code] = path;
        countries.push({
          code: code,
          x: Number(path.getAttribute("data-x")),
          y: Number(path.getAttribute("data-y")),
          area: Number(path.getAttribute("data-area")),
          small: false,
        });
      });
      places.forEach(function (place) {
        var dot = doc.createElementNS(SVG, "circle");
        dot.setAttribute("cx", place[0]);
        dot.setAttribute("cy", place[1]);
        dot.setAttribute("class", "place");
        var title = doc.createElementNS(SVG, "title");
        title.textContent = place[2];
        dot.appendChild(title);
        placesGroup.appendChild(dot);
      });

      function pixels() { return svg.getBoundingClientRect().width / view.w || 1; }

      /* Which countries are small at this zoom; they get a dot, coloured if anybody
         is from there, so they can be seen and pointed at. */
      function draw() {
        svg.setAttribute("viewBox", [view.x, view.y, view.w, view.h].join(" "));
        var scale = pixels();
        countries.forEach(function (c) {
          c.small = c.area * scale * scale < SMALL;
          var mark = marks[c.code];
          if (c.small && heats[c.code] && !mark) {
            mark = marks[c.code] = doc.createElementNS(SVG, "circle");
            mark.setAttribute("cx", c.x);
            mark.setAttribute("cy", c.y);
            mark.setAttribute("class", "small-country heat-" + heats[c.code]);
            marksGroup.appendChild(mark);
          }
          if (mark) {
            mark.setAttribute("r", c.small ? 4 / scale : 0);
          }
        });
        placesGroup.querySelectorAll("circle").forEach(function (dot) {
          dot.setAttribute("r", 2.5 / scale);
        });
      }

      function pointOf(event) {
        var rect = svg.getBoundingClientRect();
        return {
          x: view.x + (event.clientX - rect.left) / rect.width * view.w,
          y: view.y + (event.clientY - rect.top) / rect.height * view.h,
        };
      }

      function codeAt(event) {
        var path = event.target.closest && event.target.closest("path[data-country]");
        var under = path ? path.getAttribute("data-country") : null;
        return pick(under, pointOf(event), countries, NEAR / pixels());
      }

      var hovered = null;
      function hover(code, event) {
        if (hovered !== code) {
          [paths[hovered], marks[hovered]].forEach(function (e) { if (e) e.classList.remove("hover"); });
          [paths[code], marks[code]].forEach(function (e) { if (e) e.classList.add("hover"); });
          hovered = code;
        }
        if (!code) { tip.hidden = true; return; }
        var rect = box.getBoundingClientRect();
        tip.textContent = tipOf(code, tips, names, nobody);
        tip.hidden = false;
        tip.style.left = Math.min(event.clientX - rect.left + 12, rect.width - tip.offsetWidth - 4) + "px";
        tip.style.top = (event.clientY - rect.top + 12) + "px";
      }

      function show(code) {
        Object.keys(paths).forEach(function (c) { paths[c].classList.toggle("chosen", c === code); });
        var shown = false;
        details.forEach(function (section) {
          var match = section.getAttribute("data-country-detail") === code;
          section.hidden = !match;
          shown = shown || match;
        });
        if (choose) {
          choose.hidden = shown;
          if (!shown && code) choose.textContent = tipOf(code, tips, names, nobody);
        }
      }

      var pointers = {}, dragged = false, pinch = null;
      svg.addEventListener("pointerdown", function (event) {
        pointers[event.pointerId] = { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY };
        dragged = false;
        if (svg.setPointerCapture) svg.setPointerCapture(event.pointerId);
      });
      svg.addEventListener("pointermove", function (event) {
        var down = pointers[event.pointerId];
        var ids = Object.keys(pointers);
        if (down && ids.length === 2) {
          down.x = event.clientX; down.y = event.clientY;
          var a = pointers[ids[0]], b = pointers[ids[1]];
          var distance = Math.hypot(a.x - b.x, a.y - b.y);
          var middle = pointOf({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 });
          if (pinch) { view = zoom(view, pinch / distance, middle, whole); draw(); }
          pinch = distance;
          dragged = true;
          return;
        }
        if (down) {
          var scale = pixels();
          if (dragged || Math.hypot(event.clientX - down.startX, event.clientY - down.startY) > DRAG) {
            dragged = true;
            svg.classList.add("dragging");
            view = clamp({ x: view.x - (event.clientX - down.x) / scale, y: view.y - (event.clientY - down.y) / scale, w: view.w, h: view.h }, whole);
            draw();
          }
          down.x = event.clientX; down.y = event.clientY;
          return;
        }
        hover(codeAt(event), event);
      });
      function release(event) {
        var was = pointers[event.pointerId];
        delete pointers[event.pointerId];
        pinch = null;
        svg.classList.remove("dragging");
        if (was && !dragged && event.type === "pointerup") {
          var code = codeAt(event);
          if (code) win.location.hash = "country=" + code;
        }
      }
      svg.addEventListener("pointerup", release);
      svg.addEventListener("pointercancel", release);
      svg.addEventListener("pointerleave", function () { tip.hidden = true; hover(null, null); });
      svg.addEventListener("wheel", function (event) {
        event.preventDefault();
        view = zoom(view, Math.exp(event.deltaY * 0.0015), pointOf(event), whole);
        draw();
      }, { passive: false });
      box.querySelectorAll("[data-zoom]").forEach(function (button) {
        button.addEventListener("click", function () {
          var kind = button.getAttribute("data-zoom");
          var middle = { x: view.x + view.w / 2, y: view.y + view.h / 2 };
          if (kind === "reset") view = { x: whole.x, y: whole.y, w: whole.w, h: whole.h };
          else view = zoom(view, kind === "in" ? 0.6 : 1 / 0.6, middle, whole);
          draw();
        });
      });
      win.addEventListener("hashchange", function () { show(parseHash(win.location.hash)); });
      win.addEventListener("resize", draw);
      draw();
      show(parseHash(win.location.hash));
    }
  }

  var api = { parseHash: parseHash, pick: pick, zoom: zoom, clamp: clamp, tipOf: tipOf, setup: setup };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    setup(document, window);
  }
})();

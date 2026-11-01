(function () {
  function buildLightbox() {
    var lb = document.createElement("div");
    lb.className = "lightbox";
    lb.setAttribute("role", "dialog");
    lb.setAttribute("aria-modal", "true");
    lb.hidden = true;
    lb.innerHTML =
      '<button type="button" class="lb-close" data-i18n="work.close">' + t("work.close") + '</button>' +
      '<button type="button" class="lb-nav lb-prev" data-i18n-aria="work.prev" aria-label="' + t("work.prev") + '"><span class="chev chev-left"></span></button>' +
      '<figure class="lb-figure"><img alt=""><figcaption></figcaption></figure>' +
      '<button type="button" class="lb-nav lb-next" data-i18n-aria="work.next" aria-label="' + t("work.next") + '"><span class="chev chev-right"></span></button>';
    document.body.appendChild(lb);
    return lb;
  }

  function initLightbox(getTiles) {
    var lb = buildLightbox();
    var img = lb.querySelector("img");
    var cap = lb.querySelector("figcaption");
    var index = 0;

    function show(i) {
      var tiles = getTiles();
      if (!tiles.length) return;
      index = (i + tiles.length) % tiles.length;
      var tile = tiles[index];
      img.src = tile.getAttribute("data-full");
      img.alt = tile.getAttribute("data-title") || "Christian Makuku Valentin";
      cap.textContent = tile.getAttribute("data-title") || "";
    }
    function open(tile) {
      var tiles = getTiles();
      show(tiles.indexOf(tile));
      lb.hidden = false;
      document.body.classList.add("no-scroll");
      lb.querySelector(".lb-close").focus();
    }
    function close() {
      lb.hidden = true;
      img.src = "";
      document.body.classList.remove("no-scroll");
    }
    lb.addEventListener("click", function (e) {
      if (e.target.closest(".lb-close") || e.target === lb) close();
      else if (e.target.closest(".lb-prev")) show(index - 1);
      else if (e.target.closest(".lb-next")) show(index + 1);
    });
    document.addEventListener("keydown", function (e) {
      if (lb.hidden) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(index - 1);
      if (e.key === "ArrowRight") show(index + 1);
    });
    return open;
  }

  var gallery = document.getElementById("gallery");
  if (gallery) {
    var visible = function () {
      return Array.prototype.slice.call(gallery.querySelectorAll(".tile")).filter(function (t) { return !t.hidden; });
    };
    var open = initLightbox(visible);
    gallery.addEventListener("click", function (e) {
      var tile = e.target.closest(".tile");
      if (tile) open(tile);
    });
    document.querySelectorAll(".filter").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var f = btn.getAttribute("data-filter");
        document.querySelectorAll(".filter").forEach(function (b) { b.classList.toggle("active", b === btn); });
        gallery.querySelectorAll(".tile").forEach(function (tile) {
          tile.hidden = f !== "all" && tile.getAttribute("data-category") !== f;
        });
      });
    });
  }

  var recent = document.getElementById("recentGallery");
  if (recent) {
    fetch(recent.getAttribute("data-api"))
      .then(function (r) { return r.json(); })
      .then(function (items) {
        if (!items.length) {
          document.getElementById("recentEmpty").hidden = false;
          recent.hidden = true;
          return;
        }
        items.slice(0, 6).forEach(function (it) {
          var fig = document.createElement("figure");
          fig.className = "tile";
          fig.setAttribute("data-full", it.url);
          fig.setAttribute("data-title", it.title || "");
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "tile-btn";
          var im = document.createElement("img");
          im.src = it.thumb_url;
          im.alt = it.title || "Christian Makuku Valentin";
          im.loading = "lazy";
          im.width = it.width;
          im.height = it.height;
          btn.appendChild(im);
          fig.appendChild(btn);
          var cap = document.createElement("figcaption");
          if (it.title) {
            var ti = document.createElement("span");
            ti.className = "tile-title";
            ti.textContent = it.title;
            cap.appendChild(ti);
          }
          var c = document.createElement("span");
          c.className = "tile-cat";
          c.setAttribute("data-i18n", "cat." + it.category);
          c.textContent = t("cat." + it.category) || it.category;
          cap.appendChild(c);
          fig.appendChild(cap);
          recent.appendChild(fig);
        });
        var open = initLightbox(function () { return Array.prototype.slice.call(recent.querySelectorAll(".tile")); });
        recent.addEventListener("click", function (e) {
          var tile = e.target.closest(".tile");
          if (tile) open(tile);
        });
      })
      .catch(function () {
        document.getElementById("recentEmpty").hidden = false;
      });
  }
})();

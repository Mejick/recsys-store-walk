/* Магазин-бродилка: демо на реальных агрегатах Instacart.
   Скоринг в браузере = эвристика прототипа (ranked) на таблицах из site/data,
   тех же, что лежат в results/ репозитория. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  /* ROOM_TERM: "lift" = формула прототипа (симметричный lift к текущему отделу),
     "directed" = вариант 4b из metrics.md (направленный lift по переходам add_to_cart_order). */
  var ROOM_TERM = "lift";
  var KEYS = [], DEP = {}, LIFT = {}, DLIFT = {}, TRANS = {}, PROFILES = [], GROUPS = [], ITEM = {}, META = {};
  var room = "produce", sel = null, view = null, expanded = false, cart = {}, hist = {}, orders = 0, profileIdx = 0;
  var WALLS = { fresh: ["#DFF1E3", "#A8D5B3"], shelf: ["#F6E7CF", "#E2BF8E"], cold: ["#DDEFF7", "#A9D3E6"], home: ["#EDE4F5", "#C9B3E3"] };

  function f1(x) { return x.toFixed(1).replace(".", ","); }
  function pct(x) { return Math.round(x * 100) + "%"; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function pic(file, cls) { return '<img src="img/' + file + '" alt="" width="56" height="56" loading="lazy"' + (cls ? ' class="' + cls + '"' : "") + ">"; }
  function save() {
    try {
      localStorage.setItem("brodilka-cart", JSON.stringify(cart));
      localStorage.setItem("brodilka-hist", JSON.stringify({ hist: hist, orders: orders, profile: profileIdx }));
    } catch (e) { /* private mode */ }
  }
  function count() { var n = 0; for (var k in cart) n += cart[k]; return n; }
  function cartLocs() { var c = {}; for (var id in cart) c[ITEM[id].dept] = (c[ITEM[id].dept] || 0) + cart[id]; return c; }

  /* ---- scoring: the prototype's ranked() on real tables --------------------------------- */
  function ranked() {
    var cl = cartLocs(), tot = count(), hmax = 1;
    KEYS.forEach(function (k) { hmax = Math.max(hmax, hist[k] || 0); });
    return KEYS.filter(function (L) { return L !== room && !DEP[L].norec; }).map(function (L) {
      var sc = 0, topC = null, topV = 0;
      for (var c in cl) { if (c === L) continue; var t = (cl[c] / tot) * Math.log(LIFT[c][L]); sc += t; if (t > topV) { topV = t; topC = c; } }
      var sr = 0.5 * Math.log(ROOM_TERM === "directed" ? DLIFT[room][L] : LIFT[room][L]), sh = 0.6 * Math.log(1 + (hist[L] || 0)) / Math.log(1 + hmax);
      var o = { to: L, s: sc + sr + sh - (cl[L] ? 1 : 0), sc: sc, sr: sr, sh: sh, topC: topC };
      if (topC && sc >= sh && sc >= sr) { o.tag = "к корзине"; o.why = "В корзине есть «" + DEP[topC].ru.toLowerCase() + "», вместе с этим отделом берут в " + f1(LIFT[topC][L]) + " раза чаще"; }
      else if (sh >= sr && (hist[L] || 0) > 0) { o.tag = "часто берёте"; o.why = "Был в " + hist[L] + " из " + orders + " ваших заказов"; }
      else if (ROOM_TERM === "directed") { o.tag = "рядом"; o.why = "После отдела «" + DEP[room].ru + "» сюда идут следующим в " + pct(TRANS[room][L]) + " случаев, это в " + f1(DLIFT[room][L]) + " раза чаще обычного"; }
      else { o.tag = "рядом"; o.why = "С отделом «" + DEP[room].ru + "» берут в " + f1(LIFT[room][L]) + " раза чаще, после него сюда идут в " + pct(TRANS[room][L]) + " случаев"; }
      return o;
    }).sort(function (a, b) { return b.s - a.s; });
  }

  /* ---- rendering -------------------------------------------------------------------- */
  function arrowBtn(p) { return '<button class="arrow" type="button" data-go="' + p.to + '">' + pic(DEP[p.to].icon) + "<span>Дальше: " + esc(DEP[p.to].ru) + "<small>" + esc(p.why) + "</small></span><b>✦</b></button>"; }
  function objBtn(a, i) {
    var n = 0; a.products.forEach(function (p, j) { n += cart[a.id + "_" + j] || 0; });
    return '<button class="obj" type="button" data-obj="' + i + '" aria-pressed="' + (sel === i) + '" aria-label="' + esc(a.ru) + '">' + pic(a.icon) + '<span class="tg">' + esc(a.short || a.ru) + "</span>" + (n ? '<span class="n">' + n + "</span>" : "") + "</button>";
  }
  function shelvesHtml(d) {
    var show = expanded ? d.aisles : d.aisles.slice(0, d.top), objs = show.map(objBtn), h = "";
    for (var i = 0; i < objs.length; i += 5) h += '<div class="shelf">' + objs.slice(i, i + 5).join("") + "</div>";
    if (d.aisles.length > d.top) h += '<button class="more" type="button" data-more>' + (expanded ? "Свернуть" : "Ещё " + (d.aisles.length - d.top)) + "</button>";
    return '<div class="shelves">' + h + "</div>";
  }
  function render(anim) {
    var d = DEP[room], R = ranked(), el = $("room"), w = WALLS[d.group] || WALLS.shelf;
    el.style.setProperty("--w1", w[0]); el.style.setProperty("--w2", w[1]);
    var near = KEYS.filter(function (k) { return k !== room && k !== R[0].to && !DEP[k].norec && LIFT[room][k] > 1; })
      .sort(function (a, b) { return LIFT[room][b] - LIFT[room][a]; }).slice(0, 2);
    el.innerHTML = '<div class="nav"><h2>' + esc(d.ru) + "<small>" + esc(d.key) + " · в " + pct(d.share) + " заказов</small></h2>" + arrowBtn(R[0]) +
      (near.length ? '<div class="with"><span>С этим берут</span>' + near.map(function (k) { return '<button type="button" data-go="' + k + '">' + pic(DEP[k].icon) + "<span>" + esc(DEP[k].ru) + " <small>×" + f1(LIFT[room][k]) + "</small></span></button>"; }).join("") + "</div>" : "") + "</div>" + shelvesHtml(d);
    el.className = "room"; if (anim) { void el.offsetWidth; el.classList.add("enter"); }
    $("map").innerHTML = R.slice(0, 6).map(function (o, i) {
      return '<button type="button" data-go="' + o.to + '"' + (i === 0 ? ' class="pred"' : "") + ">" + pic(DEP[o.to].icon) + "<span>" + esc(DEP[o.to].ru) + "</span><small>" + (i === 0 ? "✦ прогноз" : o.tag) + "</small></button>";
    }).join("");
    $("cartN").textContent = count();
  }
  function tables() {
    var h = "<table><tr><th></th>" + KEYS.map(function (k) { return "<th>" + esc(DEP[k].ru) + "</th>"; }).join("") + "</tr>";
    KEYS.forEach(function (a) {
      h += "<tr><th>" + esc(DEP[a].ru) + "</th>" + KEYS.map(function (b) { var x = LIFT[a][b]; return a === b ? "<td>—</td>" : '<td class="' + (x > 1.2 ? "hi" : x < 0.8 ? "lo" : "") + '">' + x.toFixed(2).replace(".", ",") + "</td>"; }).join("") + "</tr>";
    });
    $("liftTable").innerHTML = h + "</table>";
    var t = "<table><tr><th>Текущий отдел</th><th>1</th><th>2</th><th>3</th></tr>";
    KEYS.forEach(function (a) {
      var top = KEYS.filter(function (b) { return b !== a; }).sort(function (x, y) { return TRANS[a][y] - TRANS[a][x]; }).slice(0, 3);
      t += "<tr><th>" + esc(DEP[a].ru) + "</th>" + top.map(function (b) { return "<td>" + esc(DEP[b].ru) + " " + pct(TRANS[a][b]) + "</td>"; }).join("") + "</tr>";
    });
    $("transTable").innerHTML = t + "</table>";
    $("howto").innerHTML = "<p>Все числа посчитаны по " + META.n_orders.toLocaleString("ru-RU") + " реальным заказам " + META.n_users.toLocaleString("ru-RU") + " покупателей Instacart (Kaggle), отделы <code>missing</code> и <code>other</code> исключены. " +
      "Lift(A,B) = P(A и B в одном заказе) / (P(A)·P(B)). Переходы построены по порядку добавления товаров в корзину (<code>add_to_cart_order</code>): для каждого товара смотрим, какой отдел, которого ещё нет в корзине, появится следующим.</p>" +
      "<p>Отделы, куда идут целенаправленно (сейчас это «Для животных»), в подсказки не попадают, но доступны через «Все отделы». Оценка отдела для стрелки и карты: сумма по отделам корзины (доля товаров × ln lift) + 0,5·ln lift к текущему отделу + 0,6·нормированная логарифмическая частота отдела в ваших прошлых заказах − 1, если отдел уже в корзине. Это эвристика из прототипа; в офлайн-замерах на тех же данных CatBoost и персональная популярность точнее, таблица метрик в README репозитория.</p>";
  }

  /* ---- sheets ------------------------------------------------------------------------ */
  var sheet, inn, X = '<button class="close" type="button" data-close aria-label="Закрыть">×</button>';
  function addBtn(id) { var q = cart[id] || 0; return '<button class="add' + (q ? " has" : "") + '" type="button" data-add="' + id + '" aria-label="Добавить в корзину">' + (q ? q + " +" : "+") + "</button>"; }
  function openObj(i) {
    sel = i; view = "obj"; var a = (expanded ? DEP[room].aisles : DEP[room].aisles.slice(0, DEP[room].top))[i];
    inn.innerHTML = X + "<h2>" + esc(a.ru) + '</h2><p class="meta">' + esc(a.key) + " · в " + a.orders.toLocaleString("ru-RU") + " заказах · топ-" + a.products.length + " товаров по числу заказов</p>" +
      '<ul class="list">' + a.products.map(function (p, j) { var id = a.id + "_" + j; return "<li><span>" + esc(p) + "</span>" + addBtn(id) + "</li>"; }).join("") + "</ul>" + arrowBtn(ranked()[0]);
    sheet.classList.add("open");
  }
  function openCart() {
    sel = null; view = "cart";
    var ids = Object.keys(cart), h = X + '<div class="cart"><h2>Корзина</h2>';
    if (!ids.length) h += '<p class="empty">Пока пусто. Нажмите на полку и добавьте товар.</p>';
    else h += "<ul>" + ids.map(function (id) { var it = ITEM[id]; return "<li><span>" + esc(it.name) + "<small>" + esc(it.aisle) + ", " + esc(DEP[it.dept].ru.toLowerCase()) + '</small></span><span class="qty"><button type="button" data-dec="' + id + '" aria-label="Убрать одну">−</button><b>' + cart[id] + '</b><button type="button" data-add="' + id + '" aria-label="Добавить одну">+</button></span></li>'; }).join("") + "</ul>" +
      '<div class="acts"><button class="btn fill" type="button" data-order>Оформить демо-заказ</button><button class="btn line" type="button" data-clear>Очистить корзину</button></div>';
    h += '<p class="note">Прошлых заказов: ' + orders + ". Демо-заказ ничего не покупает, он записывает отделы корзины в историю, по которой строятся прогноз и карта. <a href=\"#\" data-reset>Сбросить историю к профилю</a></p></div>";
    inn.innerHTML = h; sheet.classList.add("open");
  }
  function openAll() {
    sel = null; view = "all";
    inn.innerHTML = X + "<h2>Все отделы</h2>" + GROUPS.map(function (g) {
      return "<h4>" + esc(g.ru) + '</h4><div class="alld">' + KEYS.filter(function (k) { return DEP[k].group === g.key; }).map(function (k) {
        return '<button type="button" data-go="' + k + '" aria-current="' + (k === room) + '">' + pic(DEP[k].icon) + "<span>" + esc(DEP[k].ru) + "</span><small>" + pct(DEP[k].share) + " заказов</small></button>";
      }).join("") + "</div>";
    }).join("");
    sheet.classList.add("open");
  }
  function closeSheet() { sheet.classList.remove("open"); sel = null; view = null; }
  function go(to) { closeSheet(); if (to === room) { render(); return; } room = to; expanded = false; render(true); window.scrollTo({ top: 0, behavior: "auto" }); }

  /* ---- profiles & theme ------------------------------------------------------------- */
  function applyProfile(i, keepHist) {
    profileIdx = i; var p = PROFILES[i];
    if (!keepHist) { hist = {}; KEYS.forEach(function (k) { hist[k] = p.hist[k] || 0; }); orders = p.orders; }
    $("profileSel").value = String(i);
    $("profileNote").textContent = p.note + (p.share === null ? "" : " Частоты отделов взяты из центра кластера KMeans и пересчитаны на " + p.orders + " заказов.");
  }
  function setTheme(t) {
    if (t) document.documentElement.setAttribute("data-theme", t); else document.documentElement.removeAttribute("data-theme");
    try { if (t) localStorage.setItem("brodilka-theme", t); else localStorage.removeItem("brodilka-theme"); } catch (e) { /* ignore */ }
  }
  function cycleTheme() {
    var cur = document.documentElement.getAttribute("data-theme");
    setTheme(cur === "dark" ? "light" : cur === "light" ? null : "dark");
  }

  /* ---- events ---------------------------------------------------------------------- */
  function bind() {
    document.addEventListener("click", function (e) {
      var t = e.target.closest("[data-obj],[data-add],[data-dec],[data-clear],[data-order],[data-reset],[data-close],[data-go],[data-all],[data-more],#cartBtn,#themeBtn");
      if (!t) return;
      if (t.id === "themeBtn") { cycleTheme(); return; }
      if (t.id === "cartBtn") { view === "cart" ? closeSheet() : openCart(); return; }
      if (t.hasAttribute("data-all")) { openAll(); return; }
      if (t.hasAttribute("data-close")) { closeSheet(); render(); return; }
      if (t.hasAttribute("data-go")) { go(t.getAttribute("data-go")); return; }
      if (t.hasAttribute("data-more")) { expanded = !expanded; closeSheet(); render(); return; }
      if (t.hasAttribute("data-obj")) { var i = +t.getAttribute("data-obj"); if (sel === i) { closeSheet(); render(); } else { openObj(i); render(); } return; }
      if (t.hasAttribute("data-add")) { var a = t.getAttribute("data-add"); cart[a] = (cart[a] || 0) + 1; }
      if (t.hasAttribute("data-dec")) { var d = t.getAttribute("data-dec"); cart[d] = (cart[d] || 0) - 1; if (cart[d] <= 0) delete cart[d]; }
      if (t.hasAttribute("data-clear")) cart = {};
      if (t.hasAttribute("data-order")) { var cl = cartLocs(); for (var k in cl) hist[k] = (hist[k] || 0) + 1; orders++; cart = {}; }
      if (t.hasAttribute("data-reset")) { e.preventDefault(); applyProfile(profileIdx); }
      save(); render();
      if (view === "cart") openCart(); else if (sel !== null) { var sc = inn.scrollTop; openObj(sel); inn.scrollTop = sc; }
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") { closeSheet(); render(); } });
    $("profileSel").addEventListener("change", function () { applyProfile(+this.value); save(); render(true); });
  }

  /* ---- boot ------------------------------------------------------------------------ */
  function load(name) { return fetch("data/" + name + ".json", { cache: "no-cache" }).then(function (r) { if (!r.ok) throw new Error(name + ": " + r.status); return r.json(); }); }
  Promise.all([load("store"), load("lift_department"), load("transitions_department"), load("profiles"), load("meta")]).then(function (res) {
    var store = res[0], lift = res[1], trans = res[2];
    PROFILES = res[3].profiles; META = res[4]; GROUPS = store.groups;
    KEYS = lift.departments;
    store.departments.forEach(function (d) {
      d.top = store.top_aisles_shown; DEP[d.key] = d;
      d.aisles.forEach(function (a) { a.products.forEach(function (p, j) { ITEM[a.id + "_" + j] = { name: p, aisle: a.ru, dept: d.key }; }); });
    });
    KEYS.forEach(function (a, i) {
      LIFT[a] = {}; TRANS[a] = {}; DLIFT[a] = {};
      KEYS.forEach(function (b, j) { LIFT[a][b] = Math.max(0.05, lift.lift[i][j]); TRANS[a][b] = trans.p_next_given_current[i][j]; DLIFT[a][b] = Math.max(0.05, trans.directed_lift[i][j]); });
    });
    sheet = $("sheet"); inn = $("sheetIn");
    $("profileSel").innerHTML = PROFILES.map(function (p, i) { return '<option value="' + i + '">' + esc(p.title) + (p.share === null ? "" : " · " + pct(p.share)) + "</option>"; }).join("");
    var stored = null;
    try { cart = JSON.parse(localStorage.getItem("brodilka-cart") || "{}") || {}; stored = JSON.parse(localStorage.getItem("brodilka-hist") || "null"); } catch (e) { cart = {}; }
    for (var ck in cart) if (!ITEM[ck]) delete cart[ck];
    if (stored && stored.hist && PROFILES[stored.profile || 0]) { hist = stored.hist; orders = stored.orders || 0; applyProfile(stored.profile || 0, true); }
    else applyProfile(Math.min(1, PROFILES.length - 1));
    $("credit").innerHTML = "Данные: Instacart Market Basket Analysis (Kaggle), " + META.n_orders.toLocaleString("ru-RU") + " заказов, только агрегаты. Иллюстрации: Microsoft Fluent Emoji, лицензия MIT. Названия товаров оставлены английскими, как в датасете. Код и метрики: <a href=\"https://github.com/Mejick/recsys-store-walk\">репозиторий</a>.";
    // deep links for screenshots / sharing: ?room=alcohol&theme=dark&aisle=0
    var q = new URLSearchParams(location.search);
    if (q.get("theme") === "dark" || q.get("theme") === "light") setTheme(q.get("theme"));
    if (q.get("room") && DEP[q.get("room")]) room = q.get("room");
    bind(); render(); tables();
    if (q.get("aisle") !== null && !isNaN(+q.get("aisle"))) { openObj(+q.get("aisle")); render(); }
  }).catch(function (err) {
    $("room").innerHTML = '<p class="err">Не удалось загрузить данные (' + esc(err.message) + "). Откройте сайт через http-сервер, а не как файл: <code>python -m http.server -d site</code>.</p>";
  });
})();

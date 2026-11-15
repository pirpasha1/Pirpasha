// Small helpers that make data entry easier. Works without internet.
(function () {
  // Ask before deleting anything.
  document.addEventListener("submit", function (e) {
    var msg = e.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) { e.preventDefault(); return; }
    e.target.removeAttribute("data-dirty");
  });

  // Dropdowns marked "auto-submit" reload the page as soon as a choice is made.
  document.querySelectorAll("select.auto-submit, input.auto-submit").forEach(function (el) {
    el.addEventListener("change", function () { el.form.submit(); });
  });

  // Warn before leaving a page with unsaved changes.
  document.querySelectorAll("form[data-warn-unsaved]").forEach(function (form) {
    form.addEventListener("input", function () { form.setAttribute("data-dirty", "1"); });
    form.addEventListener("change", function () { form.setAttribute("data-dirty", "1"); });
  });
  window.addEventListener("beforeunload", function (e) {
    if (document.querySelector("form[data-dirty]")) { e.preventDefault(); e.returnValue = ""; }
  });

  // "Mark all" buttons: <button data-set-all="P" data-target=".att">
  document.querySelectorAll("[data-set-all]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var value = btn.getAttribute("data-set-all");
      var scope = document.querySelector(btn.getAttribute("data-scope") || "body");
      scope.querySelectorAll('input[type=radio][value="' + value + '"]').forEach(function (r) { r.checked = true; });
      scope.querySelectorAll("select[data-fill]").forEach(function (s) { s.value = value; });
      var form = btn.closest("form"); if (form) form.setAttribute("data-dirty", "1");
      updateCounts();
    });
  });

  // Live Present / Absent / Leave counter on the attendance page.
  function updateCounts() {
    var box = document.getElementById("att-counts");
    if (!box) return;
    var c = { P: 0, A: 0, L: 0 };
    document.querySelectorAll("input.att:checked").forEach(function (r) { c[r.value]++; });
    box.textContent = "Present: " + c.P + "   Absent: " + c.A + "   Leave: " + c.L;
  }
  document.addEventListener("change", function (e) { if (e.target.classList.contains("att")) updateCounts(); });
  updateCounts();

  // In mark-entry grids, Enter moves to the next box instead of submitting.
  document.querySelectorAll("input.mark-input").forEach(function (input, i, all) {
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === "ArrowDown") {
        e.preventDefault();
        if (all[i + 1]) { all[i + 1].focus(); all[i + 1].select(); }
      } else if (e.key === "ArrowUp" && all[i - 1]) {
        e.preventDefault(); all[i - 1].focus(); all[i - 1].select();
      }
    });
    input.addEventListener("input", function () {
      var max = parseFloat(input.getAttribute("data-max"));
      var v = input.value.trim().toUpperCase();
      var bad = v !== "" && v !== "AB" && (isNaN(parseFloat(v)) || parseFloat(v) < 0 || parseFloat(v) > max);
      input.style.background = bad ? "#fbe9eb" : "";
      input.title = bad ? "Marks must be between 0 and " + max + " (or AB for absent)" : "";
    });
  });

  // Quick filter box for long tables: <input data-filter="#tableId">
  document.querySelectorAll("input[data-filter]").forEach(function (input) {
    var table = document.querySelector(input.getAttribute("data-filter"));
    input.addEventListener("input", function () {
      var q = input.value.toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        tr.style.display = tr.textContent.toLowerCase().indexOf(q) === -1 ? "none" : "";
      });
    });
  });

  // Insert a suggested remark into the textarea.
  document.querySelectorAll("[data-remark-target]").forEach(function (sel) {
    sel.addEventListener("change", function () {
      var ta = document.getElementById(sel.getAttribute("data-remark-target"));
      if (sel.value) { ta.value = ta.value ? ta.value + " " + sel.value : sel.value; sel.value = ""; }
    });
  });

  // Mobile menu
  var toggle = document.querySelector(".menu-toggle");
  if (toggle) toggle.addEventListener("click", function () {
    document.querySelector(".sidebar").classList.toggle("open");
  });

  // "Select all" checkbox
  document.querySelectorAll("input[data-check-all]").forEach(function (box) {
    box.addEventListener("change", function () {
      document.querySelectorAll(box.getAttribute("data-check-all")).forEach(function (c) { c.checked = box.checked; });
    });
  });
})();

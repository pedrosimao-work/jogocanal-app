"use strict";
(() => {
  const input = document.querySelector("#schedule-search");
  if (!input) return;
  const rows = [...document.querySelectorAll(".schedule-match")];
  const fold = value => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-PT");
  const update = () => {
    const terms = fold(input.value).trim().split(/\s+/).filter(Boolean);
    let count = 0;
    rows.forEach(row => {
      row.hidden = !terms.every(term => fold(row.dataset.search).includes(term));
      if (!row.hidden) count++;
    });
    document.querySelectorAll(".schedule-day").forEach(day => {
      day.hidden = terms.length > 0 && ![...day.querySelectorAll(".schedule-match")].some(row => !row.hidden);
    });
    document.querySelector("#result-count").textContent = `${count} ${count === 1 ? "jogo" : "jogos"}`;
    document.querySelector("#search-empty").hidden = !terms.length || count > 0;
  };
  input.addEventListener("input", update);
  update();
})();

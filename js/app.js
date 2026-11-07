// Main Application Logic for SPINORAMA JPY

let state = {
  search: "",
  brand: "",
  shape: "",
  energy: "",
  availability: "available",
  min_price: "",
  max_price: "",
  sort: "score_tone",
  order: "desc",
  page: 1,
  limit: 50,
  total: 0,
  speakers: []
};

// DOM Elements
const searchInput = document.getElementById("searchInput");
const filterAvailability = document.getElementById("filterAvailability");
const filterBrand = document.getElementById("filterBrand");
const filterShape = document.getElementById("filterShape");
const filterEnergy = document.getElementById("filterEnergy");
const minPriceInput = document.getElementById("minPriceInput");
const maxPriceInput = document.getElementById("maxPriceInput");
const applyPriceBtn = document.getElementById("applyPriceBtn");
const resetFilterBtn = document.getElementById("resetFilterBtn");
const sortSelect = document.getElementById("sortSelect");

const speakersTbody = document.getElementById("speakersTbody");
const resultsCount = document.getElementById("resultsCount");
const paginationInfo = document.getElementById("paginationInfo");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");

const themeToggleBtn = document.getElementById("themeToggleBtn");
const themeIcon = document.getElementById("themeIcon");
const triggerUpdateBtn = document.getElementById("triggerUpdateBtn");

const thCpCol = document.getElementById("thCpCol");

// Initialize
async function initApp() {
  initTheme();
  initTabs();
  await loadStats();
  await loadBrands();
  await fetchSpeakers();
}

// Navigation Tabs
window.switchTab = function(tabName) {
  const tabRanking = document.getElementById("tabBtnRanking");
  const tabVerification = document.getElementById("tabBtnVerification");
  const rankingView = document.getElementById("rankingView");
  const verificationView = document.getElementById("verificationView");

  if (tabName === "verification") {
    if (tabVerification) tabVerification.classList.add("active");
    if (tabRanking) tabRanking.classList.remove("active");
    if (rankingView) rankingView.style.display = "none";
    if (verificationView) verificationView.style.display = "block";
  } else {
    if (tabRanking) tabRanking.classList.add("active");
    if (tabVerification) tabVerification.classList.remove("active");
    if (rankingView) rankingView.style.display = "block";
    if (verificationView) verificationView.style.display = "none";
    if (window.renderScatterPlot) {
      window.renderScatterPlot();
    }
  }
};

function initTabs() {
  const tabRanking = document.getElementById("tabBtnRanking");
  const tabVerification = document.getElementById("tabBtnVerification");

  if (tabRanking) {
    tabRanking.addEventListener("click", () => window.switchTab("ranking"));
  }
  if (tabVerification) {
    tabVerification.addEventListener("click", () => window.switchTab("verification"));
  }
}

// Theme
function initTheme() {
  const saved = localStorage.getItem("spinorama_theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  themeIcon.textContent = saved === "dark" ? "☀️" : "🌙";

  themeToggleBtn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("spinorama_theme", next);
    themeIcon.textContent = next === "dark" ? "☀️" : "🌙";
    if (window.renderScatterPlot) {
      window.renderScatterPlot();
    }
  });
}

let isStaticMode = false;
window.isStaticMode = false;
let allStaticSpeakers = null;

// Helper to populate stats DOM
function setStatsData(data) {
  document.getElementById("kpiTotal").textContent = data.total_speakers.toLocaleString();
  document.getElementById("kpiDomestic").textContent = data.domestic_in_stock.toLocaleString();
  document.getElementById("kpiManual").textContent = data.manual_overrides.toLocaleString();
  
  if (data.last_updated) {
    const d = new Date(data.last_updated);
    document.getElementById("kpiUpdated").textContent = `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  } else {
    document.getElementById("kpiUpdated").textContent = "未実行";
  }
}

// Load KPI Stats
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) throw new Error("API not available");
    const data = await res.json();
    setStatsData(data);
  } catch (err) {
    // Switch to static mode (e.g. Cloudflare Pages)
    isStaticMode = true;
    window.isStaticMode = true;
    try {
      const res = await fetch("data/stats.json");
      const data = await res.json();
      setStatsData(data);

      const csvBtn = document.getElementById("csvExportBtn");
      if (csvBtn) {
        csvBtn.href = "data/spinorama_jpy.csv";
        csvBtn.download = "spinorama_jpy.csv";
      }

      const brandLogo = document.querySelector(".brand-section");
      if (brandLogo && !document.getElementById("staticBadge")) {
        const badge = document.createElement("span");
        badge.id = "staticBadge";
        badge.className = "badge badge-import";
        badge.style.marginLeft = "0.75rem";
        badge.style.fontSize = "0.75rem";
        badge.style.verticalAlign = "middle";
        badge.textContent = "Pages 静的配信版";
        brandLogo.appendChild(badge);
      }
    } catch (e2) {
      console.error("Failed to load static stats:", e2);
    }
  }
}

// Load Brands for filter dropdown
async function loadBrands() {
  try {
    const url = isStaticMode ? "data/brands.json" : "/api/brands";
    const res = await fetch(url);
    const data = await res.json();
    filterBrand.innerHTML = '<option value="">すべてのメーカー (All)</option>';
    data.brands.forEach(b => {
      const opt = document.createElement("option");
      opt.value = b;
      opt.textContent = b;
      filterBrand.appendChild(opt);
    });
  } catch (err) {
    if (!isStaticMode) {
      isStaticMode = true;
      window.isStaticMode = true;
      return loadBrands();
    }
    console.error("Failed to load brands:", err);
  }
}

// In-memory filter and sort for static mode (Cloudflare Pages)
function filterAndSortStaticSpeakers() {
  if (!allStaticSpeakers) return [];

  let list = allStaticSpeakers.filter(s => {
    // Search keyword
    if (state.search) {
      const q = state.search.toLowerCase();
      const match = (s.brand && s.brand.toLowerCase().includes(q)) ||
                    (s.model && s.model.toLowerCase().includes(q)) ||
                    (s.speaker_name && s.speaker_name.toLowerCase().includes(q));
      if (!match) return false;
    }
    // Brand
    if (state.brand && s.brand !== state.brand) return false;
    // Shape
    if (state.shape && s.shape !== state.shape) return false;
    // Energy
    if (state.energy && s.energy_type !== state.energy) return false;

    // Availability
    const avail = s.availability || "unconfirmed";
    if (state.availability === "available") {
      if (avail === "not_available") return false;
    } else if (state.availability !== "all") {
      if (avail !== state.availability) return false;
    }

    // Price
    const isUnavail = s.verification_status === "unavailable" || s.availability === "not_available";
    const p = isUnavail ? null : (s.price_jpy || (s.price_usd ? Math.round(s.price_usd * 155) : null));
    if (state.min_price && (p === null || p < Number(state.min_price))) return false;
    if (state.max_price && (p === null || p > Number(state.max_price))) return false;

    return true;
  });

  // Sort
  const sortKey = state.sort;
  const isAsc = state.order === "asc";
  list.sort((a, b) => {
    let valA = a[sortKey];
    let valB = b[sortKey];

    if (sortKey === "price_jpy") {
      const isUnavailA = a.verification_status === "unavailable" || a.availability === "not_available";
      const isUnavailB = b.verification_status === "unavailable" || b.availability === "not_available";
      valA = isUnavailA ? null : (a.price_jpy || (a.price_usd ? a.price_usd * 155 : null));
      valB = isUnavailB ? null : (b.price_jpy || (b.price_usd ? b.price_usd * 155 : null));
    }

    if (valA === null || valA === undefined) return 1;
    if (valB === null || valB === undefined) return -1;

    if (typeof valA === "string") {
      return isAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return isAsc ? valA - valB : valB - valA;
  });

  return list;
}

// Fetch Speakers (API or Static JSON)
async function fetchSpeakers() {
  resultsCount.textContent = "データを読み込み中...";
  speakersTbody.innerHTML = `<tr><td colspan="13" style="text-align:center; padding: 2rem; color: var(--text-muted);">読み込み中...</td></tr>`;

  if (isStaticMode) {
    if (!allStaticSpeakers) {
      try {
        const res = await fetch("data/speakers.json");
        const data = await res.json();
        allStaticSpeakers = Array.isArray(data) ? data : (data.items || []);
        window.allStaticSpeakers = allStaticSpeakers;
      } catch (err) {
        console.error("Failed to load static speakers:", err);
        speakersTbody.innerHTML = `<tr><td colspan="13" style="text-align:center; padding: 2rem; color: var(--accent-rose);">静的データの取得に失敗しました。</td></tr>`;
        return;
      }
    }
    const filtered = filterAndSortStaticSpeakers();
    state.total = filtered.length;
    const start = (state.page - 1) * state.limit;
    state.speakers = filtered.slice(start, start + state.limit);
    renderTable();
    updatePagination();
    if (window.initScatterPlot) {
      window.initScatterPlot(state.speakers);
    }
    return;
  }

  const params = new URLSearchParams({
    search: state.search,
    brand: state.brand,
    shape: state.shape,
    energy: state.energy,
    availability: state.availability,
    min_price: state.min_price,
    max_price: state.max_price,
    sort: state.sort,
    order: state.order,
    page: state.page,
    limit: state.limit
  });

  try {
    const res = await fetch(`/api/speakers?${params.toString()}`);
    if (!res.ok) throw new Error("API failed");
    const data = await res.json();

    state.total = data.total;
    state.speakers = data.items;

    renderTable();
    updatePagination();

    // Also update scatter plot with current results
    if (window.initScatterPlot) {
      window.initScatterPlot(state.speakers);
    }
  } catch (err) {
    console.warn("Falling back to static mode...", err);
    isStaticMode = true;
    window.isStaticMode = true;
    return fetchSpeakers();
  }
}

// Render Table
function renderTable() {
  resultsCount.textContent = `表示中: ${state.total} 件中 ${(state.page-1)*state.limit + 1} 〜 ${Math.min(state.page*state.limit, state.total)} 件`;

  if (state.speakers.length === 0) {
    speakersTbody.innerHTML = `<tr><td colspan="13" style="text-align:center; padding: 3rem; color: var(--text-muted);">該当するスピーカーが見つかりませんでした。条件を変更してお試しください。</td></tr>`;
    return;
  }

  // Update CP column header title according to current sort
  if (state.sort.startsWith("cp_tone_sub_eq")) {
    thCpCol.textContent = "Bothコスパ";
  } else if (state.sort.startsWith("cp_tone_eq")) {
    thCpCol.textContent = "EQコスパ";
  } else if (state.sort.startsWith("cp_tone_sub")) {
    thCpCol.textContent = "Subコスパ";
  } else {
    thCpCol.textContent = "Toneコスパ";
  }

  const html = state.speakers.map(s => {
    const isUnavailable = s.verification_status === "unavailable" || s.availability === "not_available";
    const priceUSD = s.price_usd ? `$${Math.round(s.price_usd).toLocaleString()}` : "---";
    
    let priceJPY = "---";
    let priceSubText = s.price_type === 'each' ? '1本価格' : 'ペア換算';
    if (isUnavailable) {
      priceJPY = `<span style="color: var(--accent-rose); font-weight: 600;">価格不明</span>`;
      priceSubText = `<span style="color: var(--accent-rose);">国内流通なし</span>`;
    } else if (s.effective_price_jpy || s.price_jpy) {
      priceJPY = `¥${(s.effective_price_jpy || s.price_jpy).toLocaleString()}`;
    }
    const isManual = s.is_manual_override === 1;

    // Availability Badge
    let availBadge = "";
    if (isUnavailable) {
      availBadge = `<span class="badge badge-discontinued" style="background: rgba(244,63,94,0.15); color: var(--accent-rose); border-color: rgba(244,63,94,0.3);" title="${s.notes || ''}">国内流通なし</span>`;
    } else if (s.availability === "domestic_in_stock") {
      availBadge = `<span class="badge badge-in-stock" title="${s.notes || ''}">国内正規品</span>`;
    } else if (s.availability === "domestic_backorder") {
      availBadge = `<span class="badge badge-in-stock" style="opacity: 0.8;" title="${s.notes || ''}">国内取寄</span>`;
    } else if (s.availability === "import_only") {
      availBadge = `<span class="badge badge-import" title="${s.notes || ''}">並行 / 海外</span>`;
    } else if (s.availability === "discontinued") {
      availBadge = `<span class="badge badge-discontinued" title="${s.notes || ''}">ディスコン</span>`;
    } else {
      availBadge = `<span class="badge badge-unconfirmed" title="${s.notes || ''}">未調査</span>`;
    }

    // Reviews
    let reviewsHtml = "---";
    if (s.reviews && s.reviews.length > 0) {
      reviewsHtml = s.reviews.map(r => `<span style="font-size:0.75rem; background: rgba(56,189,248,0.1); color: var(--accent-cyan); padding: 0.1rem 0.35rem; border-radius: 4px;">${r.source}</span>`).join(" ");
    }

    // F3 and Flatness
    const f3Html = s.f3 !== null ? `${Math.round(s.f3)}Hz` : "---";
    const flatHtml = s.flatness !== null ? `${s.flatness}dB` : "---";

    // Scores
    const formatScore = (val) => {
      if (val === null || isNaN(val)) return `<span style="color: var(--text-muted)">---</span>`;
      const num = parseFloat(val);
      let cls = "score-low";
      if (num >= 6.0) cls = "score-high";
      else if (num >= 4.0) cls = "score-mid";
      return `<span class="score-cell ${cls}">${num.toFixed(1)}</span>`;
    };

    // Cost-Performance (CPI: Cost-Performance Index)
    let cpHtml = "---";
    if (!isUnavailable) {
      let cpVal = s.cp_tone;
      if (state.sort.startsWith("cp_tone_sub_eq")) cpVal = s.cp_tone_sub_eq;
      else if (state.sort.startsWith("cp_tone_eq")) cpVal = s.cp_tone_eq;
      else if (state.sort.startsWith("cp_tone_sub")) cpVal = s.cp_tone_sub;

      if (cpVal !== null && !isNaN(cpVal)) {
        const valNum = parseFloat(cpVal);
        let cls = "cp-negative";
        if (valNum >= 2.0) cls = "cp-positive";
        else if (valNum >= 1.0) cls = "score-mid";
        cpHtml = `<span class="cp-badge ${cls}" title="音質対価格効率 (CPI)">${valNum.toFixed(2)}</span>`;
      } else {
        // 未確定機種の参考CPI（為替換算ベース）
        let estVal = s.cp_tone_est;
        if (state.sort.startsWith("cp_tone_sub_eq")) estVal = s.cp_tone_sub_eq_est;
        else if (state.sort.startsWith("cp_tone_eq")) estVal = s.cp_tone_eq_est;
        else if (state.sort.startsWith("cp_tone_sub")) estVal = s.cp_tone_sub_est;

        if (estVal !== null && !isNaN(estVal)) {
          cpHtml = `<span class="cp-badge" style="opacity: 0.45; border-style: dashed;" title="国内価格が未確定のため順位対象外 (参考CPI)">≈${parseFloat(estVal).toFixed(2)}</span>`;
        }
      }
    }

    // Verification Status Badge
    let verifBadge = "";
    const vStatus = s.verification_status || "unverified";
    if (vStatus === "verified") {
      verifBadge = `<div style="margin-top: 3px;"><span class="status-badge verified" style="font-size: 0.68rem; padding: 2px 6px;">🟢 検証済</span></div>`;
    } else if (vStatus === "needs_review") {
      verifBadge = `<div style="margin-top: 3px;"><span class="status-badge needs_review" style="font-size: 0.68rem; padding: 2px 6px;">🟡 要確認</span></div>`;
    } else if (vStatus === "unavailable") {
      verifBadge = `<div style="margin-top: 3px;"><span class="status-badge unavailable" style="font-size: 0.68rem; padding: 2px 6px;">🚫 入手不可</span></div>`;
    } else {
      verifBadge = `<div style="margin-top: 3px;"><span class="status-badge unverified" style="font-size: 0.68rem; padding: 2px 6px;">🔴 未検証</span></div>`;
    }

    return `
      <tr data-id="${s.id}">
        <td>
          <div class="speaker-title-cell">${s.brand} ${s.model}</div>
          <div class="speaker-subinfo">
            <span>${s.shape || 'bookshelf'}</span>
            <span>•</span>
            <span>${s.energy_type || 'passive'}</span>
            ${isManual ? '<span style="color: var(--accent-purple); font-weight: 700;">[手動固定]</span>' : ''}
          </div>
        </td>
        <td class="price-usd">${priceUSD}</td>
        <td>
          <div class="price-jpy">${priceJPY}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${priceSubText}</div>
          ${s.source_name ? `<div style="font-size: 0.7rem; color: var(--accent-cyan); margin-top: 2px;">📍 ${s.source_name}</div>` : ''}
          ${s.last_checked ? `<div style="font-size: 0.68rem; color: var(--text-muted);">${new Date(s.last_checked).toLocaleDateString('ja-JP', {month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit'})} 調査</div>` : ''}
        </td>
        <td>
          ${availBadge}
          ${verifBadge}
        </td>
        <td>${reviewsHtml}</td>
        <td style="font-family: var(--font-mono);">${f3Html}</td>
        <td style="font-family: var(--font-mono);">${flatHtml}</td>
        <td>${formatScore(s.score_tone)}</td>
        <td>${formatScore(s.score_tone_sub)}</td>
        <td>${formatScore(s.score_tone_eq)}</td>
        <td>${formatScore(s.score_tone_sub_eq)}</td>
        <td>${cpHtml}</td>
        <td style="text-align: center;">
          <div style="display: flex; gap: 4px; justify-content: center; align-items: center;">
            <button class="btn btn-sm btn-verify" data-id="${s.id}" title="確からしさ検証スタジオで開く" style="background: rgba(6, 182, 212, 0.15); border: 1px solid var(--accent-cyan); color: var(--accent-cyan); font-size: 0.75rem; padding: 3px 8px;">
              🎯 調査
            </button>
            <button class="btn btn-sm btn-edit" data-id="${s.id}" title="価格・入手性をクイック編集">
              ✏️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  speakersTbody.innerHTML = html;

  // Attach click listener to verify buttons
  speakersTbody.querySelectorAll(".btn-verify").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = parseInt(btn.getAttribute("data-id"));
      if (window.openVerificationForSpeaker) {
        window.openVerificationForSpeaker(id);
      }
    });
  });

  // Attach click listener to edit buttons
  speakersTbody.querySelectorAll(".btn-edit").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = parseInt(btn.getAttribute("data-id"));
      const speaker = state.speakers.find(s => s.id === id);
      if (speaker && window.openEditModal) {
        window.openEditModal(speaker);
      }
    });
  });

  speakersTbody.querySelectorAll("tr").forEach(tr => {
    tr.style.cursor = "pointer";
    tr.addEventListener("click", () => {
      const id = parseInt(tr.getAttribute("data-id"));
      const speaker = state.speakers.find(s => s.id === id);
      if (speaker && window.openEditModal) {
        window.openEditModal(speaker);
      }
    });
  });
}

// Pagination logic
function updatePagination() {
  const maxPage = Math.ceil(state.total / state.limit) || 1;
  if (paginationInfo) paginationInfo.textContent = `ページ ${state.page} / ${maxPage}`;
  if (prevPageBtn) prevPageBtn.disabled = state.page <= 1;
  if (nextPageBtn) nextPageBtn.disabled = state.page >= maxPage;
}

if (prevPageBtn) {
  prevPageBtn.addEventListener("click", () => {
    if (state.page > 1) {
      state.page--;
      fetchSpeakers();
    }
  });
}

if (nextPageBtn) {
  nextPageBtn.addEventListener("click", () => {
    const maxPage = Math.ceil(state.total / state.limit) || 1;
    if (state.page < maxPage) {
      state.page++;
      fetchSpeakers();
    }
  });
}

// Event Listeners for Filters
let searchTimeout = null;
searchInput.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    state.search = e.target.value.trim();
    state.page = 1;
    fetchSpeakers();
  }, 350);
});

filterAvailability.addEventListener("change", (e) => {
  state.availability = e.target.value;
  state.page = 1;
  fetchSpeakers();
});

filterBrand.addEventListener("change", (e) => {
  state.brand = e.target.value;
  state.page = 1;
  fetchSpeakers();
});

filterShape.addEventListener("change", (e) => {
  state.shape = e.target.value;
  state.page = 1;
  fetchSpeakers();
});

filterEnergy.addEventListener("change", (e) => {
  state.energy = e.target.value;
  state.page = 1;
  fetchSpeakers();
});

applyPriceBtn.addEventListener("click", () => {
  state.min_price = minPriceInput.value.trim();
  state.max_price = maxPriceInput.value.trim();
  state.page = 1;
  fetchSpeakers();
});

resetFilterBtn.addEventListener("click", () => {
  searchInput.value = "";
  filterAvailability.value = "available";
  filterBrand.value = "";
  filterShape.value = "";
  filterEnergy.value = "";
  minPriceInput.value = "";
  maxPriceInput.value = "";
  sortSelect.value = "score_tone";

  state.search = "";
  state.availability = "available";
  state.brand = "";
  state.shape = "";
  state.energy = "";
  state.min_price = "";
  state.max_price = "";
  state.sort = "score_tone";
  state.order = "desc";
  state.page = 1;

  fetchSpeakers();
});

// Sort Select
sortSelect.addEventListener("change", (e) => {
  const val = e.target.value;
  if (val === "price_jpy_asc") {
    state.sort = "price_jpy";
    state.order = "asc";
  } else if (val === "price_jpy_desc") {
    state.sort = "price_jpy";
    state.order = "desc";
  } else if (val === "price_usd_asc") {
    state.sort = "price_usd";
    state.order = "asc";
  } else {
    state.sort = val;
    state.order = "desc";
  }
  state.page = 1;
  updateTableHeaderSortIndicators();
  fetchSpeakers();
});

// Table Header Click Sorting
document.querySelectorAll(".scores-table th.sortable").forEach(th => {
  th.addEventListener("click", () => {
    const key = th.getAttribute("data-sort");
    if (state.sort === key) {
      state.order = state.order === "asc" ? "desc" : "asc";
    } else {
      state.sort = key;
      state.order = key.includes("price") ? "asc" : "desc";
    }
    state.page = 1;
    updateTableHeaderSortIndicators();
    fetchSpeakers();
  });
});

function updateTableHeaderSortIndicators() {
  document.querySelectorAll(".scores-table th.sortable").forEach(th => {
    const key = th.getAttribute("data-sort");
    if (state.sort === key) {
      th.classList.add("active-sort");
    } else {
      th.classList.remove("active-sort");
    }
  });
}

// Trigger Manual Full Update
triggerUpdateBtn.addEventListener("click", async () => {
  if (isStaticMode) {
    alert("【Cloudflare Pages 静的配信版】\n本サイトは高速配信用の静的スナップショットです。\n\n最新データへの更新は、自宅Linux上でデータ巡回を実行し、Cloudflare Pagesへ再デプロイしてください。");
    return;
  }
  if (!confirm("SPINORAMA公式データおよび日本市場データの最新同期を実行しますか？（数十秒かかる場合があります）")) {
    return;
  }
  triggerUpdateBtn.disabled = true;
  triggerUpdateBtn.textContent = "⏳ 更新中...";
  try {
    const res = await fetch("/api/trigger_update", { method: "POST" });
    const data = await res.json();
    alert(data.message);
    await loadStats();
    await fetchSpeakers();
  } catch (err) {
    alert("更新エラー: " + err.message);
  } finally {
    triggerUpdateBtn.disabled = false;
    triggerUpdateBtn.textContent = "🔄 データ更新";
  }
});

// Global refresh callback
window.refreshApp = async () => {
  await loadStats();
  await fetchSpeakers();
};

// Start
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}

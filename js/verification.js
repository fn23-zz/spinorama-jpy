// Price Verification Studio Logic
// Handles verified market price confirmation, one-click web search assistant, and fast workflow.

(function () {
  let vState = {
    filter: "all",
    priority: "cpi_desc",
    brand: "",
    search: "",
    page: 1,
    limit: 300,
    items: [],
    total: 0,
    activeIndex: -1,
    activeItem: null,
    stats: null
  };

  // DOM Elements
  const verifyProgressPct = document.getElementById("verifyProgressPct");
  const verifyProgressBarFill = document.getElementById("verifyProgressBarFill");
  const statTotalCount = document.getElementById("statTotalCount");
  const statUnverifiedCount = document.getElementById("statUnverifiedCount");
  const statNeedsReviewCount = document.getElementById("statNeedsReviewCount");
  const statVerifiedCount = document.getElementById("statVerifiedCount");
  const statUnavailableCount = document.getElementById("statUnavailableCount");
  const tabUnverifiedBadge = document.getElementById("tabUnverifiedBadge");

  const verifierSearchInput = document.getElementById("verifierSearchInput");
  const verifierPrioritySelect = document.getElementById("verifierPrioritySelect");
  const verifierBrandSelect = document.getElementById("verifierBrandSelect");
  const verifierListCount = document.getElementById("verifierListCount");
  const verifierActiveIndex = document.getElementById("verifierActiveIndex");
  const verifierItemsContainer = document.getElementById("verifierItemsContainer");

  // Active item displays
  const actSpkTitle = document.getElementById("actSpkTitle");
  const actSpkPriceUsd = document.getElementById("actSpkPriceUsd");
  const actSpkToneScore = document.getElementById("actSpkToneScore");
  const actSpkF3 = document.getElementById("actSpkF3");
  const actSpkCPI = document.getElementById("actSpkCPI");
  const actSpkCurrentJpy = document.getElementById("actSpkCurrentJpy");
  const actSpkBadgeContainer = document.getElementById("actSpkBadgeContainer");

  // Search Assistant Elements
  const assistantKeywordInput = document.getElementById("assistantKeywordInput");
  const btnCopyKeyword = document.getElementById("btnCopyKeyword");
  const copyIcon = document.getElementById("copyIcon");
  const copyText = document.getElementById("copyText");
  const keywordChipsContainer = document.getElementById("keywordChipsContainer");

  const btnSearchGoogle = document.getElementById("btnSearchGoogle");
  const btnSearchKakaku = document.getElementById("btnSearchKakaku");
  const btnSearchSoundhouse = document.getElementById("btnSearchSoundhouse");
  const btnSearchAmazon = document.getElementById("btnSearchAmazon");
  const btnSearchYodobashi = document.getElementById("btnSearchYodobashi");

  // Input Form Elements
  const vSpeakerId = document.getElementById("vSpeakerId");
  const vSourceUrl = document.getElementById("vSourceUrl");
  const btnTestUrl = document.getElementById("btnTestUrl");
  const vSearchKeyword = document.getElementById("vSearchKeyword");
  const vSourceName = document.getElementById("vSourceName");
  const vPriceEach = document.getElementById("vPriceEach");
  const btnCalcPairFromEach = document.getElementById("btnCalcPairFromEach");
  const vPriceJpy = document.getElementById("vPriceJpy");
  const vPriceType = document.getElementById("vPriceType");
  const vAvailability = document.getElementById("vAvailability");
  const vVerificationStatus = document.getElementById("vVerificationStatus");
  const vConfidenceLevel = document.getElementById("vConfidenceLevel");
  const vNotes = document.getElementById("vNotes");
  const btnQuickSetUnavailable = document.getElementById("btnQuickSetUnavailable");

  // Actions
  const btnPrevSpeaker = document.getElementById("btnPrevSpeaker");
  const btnNextSpeaker = document.getElementById("btnNextSpeaker");
  const btnSaveOnly = document.getElementById("btnSaveOnly");
  const btnSaveAndNext = document.getElementById("btnSaveAndNext");

  // Status Filter Chips
  const filterChips = document.querySelectorAll(".progress-stat-chips .stat-chip");

  // Initialize
  async function initVerificationStudio() {
    setupEventListeners();
    await loadVerificationStats();
    await loadVerificationBrands();
    await fetchVerificationSpeakers();
  }

  // Event Listeners Setup
  function setupEventListeners() {
    // Filter chips
    filterChips.forEach(chip => {
      chip.addEventListener("click", () => {
        filterChips.forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        vState.filter = chip.getAttribute("data-vfilter");
        fetchVerificationSpeakers();
      });
    });

    // Sidebar controls
    let searchDebounce = null;
    verifierSearchInput.addEventListener("input", (e) => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        vState.search = e.target.value.trim();
        fetchVerificationSpeakers();
      }, 300);
    });

    verifierPrioritySelect.addEventListener("change", (e) => {
      vState.priority = e.target.value;
      fetchVerificationSpeakers();
    });

    verifierBrandSelect.addEventListener("change", (e) => {
      vState.brand = e.target.value;
      fetchVerificationSpeakers();
    });

    // Copy keyword
    btnCopyKeyword.addEventListener("click", copySearchKeyword);

    // Dynamic search link update when user edits keyword
    assistantKeywordInput.addEventListener("input", () => {
      const kw = assistantKeywordInput.value.trim();
      updateSearchLinks(kw);
      vSearchKeyword.value = kw;
    });

    // Open Test URL
    btnTestUrl.addEventListener("click", () => {
      const url = vSourceUrl.value.trim();
      if (!url) {
        alert("調査先URLが入力されていません。");
        return;
      }
      window.open(url, "_blank", "noopener,noreferrer");
    });

    // Quick shop tags
    document.querySelectorAll(".quick-tag").forEach(tag => {
      tag.addEventListener("click", () => {
        vSourceName.value = tag.getAttribute("data-tag");
      });
    });

    // 1本価格とペア価格の双方向リアルタイム自動連動
    let isSyncingPrice = false;

    vPriceEach.addEventListener("input", () => {
      if (isSyncingPrice) return;
      isSyncingPrice = true;
      const raw = vPriceEach.value.trim();
      if (raw === "") {
        // if each is cleared, pair is not necessarily cleared, or leave as is
      } else {
        const eachVal = parseInt(raw, 10);
        if (!isNaN(eachVal) && eachVal >= 0) {
          vPriceJpy.value = eachVal * 2;
          vPriceType.value = "pair";
        }
      }
      isSyncingPrice = false;
    });

    vPriceJpy.addEventListener("input", () => {
      if (isSyncingPrice) return;
      isSyncingPrice = true;
      const raw = vPriceJpy.value.trim();
      if (raw === "") {
        // leave as is
      } else {
        const pairVal = parseInt(raw, 10);
        if (!isNaN(pairVal) && pairVal >= 0) {
          vPriceEach.value = Math.round(pairVal / 2);
        }
      }
      isSyncingPrice = false;
    });

    // 1本単価からペア換算 (×2) 明示ボタン
    btnCalcPairFromEach.addEventListener("click", () => {
      const eachVal = parseInt(vPriceEach.value, 10);
      if (isNaN(eachVal) || eachVal <= 0) {
        alert("有効な1本単価を入力してください。");
        return;
      }
      const pairVal = eachVal * 2;
      vPriceJpy.value = pairVal;
      vPriceType.value = "pair";
      if (!vNotes.value.includes("1本")) {
        const noteAddition = `1本あたり約${eachVal.toLocaleString()}円 (ペア換算: ${pairVal.toLocaleString()}円)`;
        vNotes.value = vNotes.value ? `${vNotes.value} / ${noteAddition}` : noteAddition;
      }
      showToast(`1本 ${eachVal.toLocaleString()}円 × 2 ＝ ペア ${pairVal.toLocaleString()}円 を設定しました`);
    });

    // Quick set unavailable
    btnQuickSetUnavailable.addEventListener("click", () => {
      vPriceJpy.value = "";
      vPriceEach.value = "";
      vAvailability.value = "not_available";
      vVerificationStatus.value = "unavailable";
      vConfidenceLevel.value = "high";
      vSourceName.value = "国内流通なし確認";
      if (!vNotes.value) {
        vNotes.value = "日本国内での正規流通・市販なし（海外限定/DIY/部品/生産完了）";
      }
      actSpkCurrentJpy.textContent = "設定値: 価格不明 (国内流通なし)";
      actSpkCurrentJpy.style.color = "var(--accent-rose)";
      actSpkCPI.textContent = "CPI: ---";
      actSpkBadgeContainer.innerHTML = getStatusBadgeHtml("unavailable", true);
      showToast("「国内流通なし・価格不明」に設定しました");
    });

    // When user selects "unavailable" in status dropdown, auto-clear prices
    vVerificationStatus.addEventListener("change", () => {
      if (vVerificationStatus.value === "unavailable") {
        vPriceJpy.value = "";
        vPriceEach.value = "";
        vAvailability.value = "not_available";
        actSpkCurrentJpy.textContent = "設定値: 価格不明 (国内流通なし)";
        actSpkCurrentJpy.style.color = "var(--accent-rose)";
        actSpkCPI.textContent = "CPI: ---";
        showToast("国内流通なしのため価格をクリア（価格不明）に設定しました");
      }
    });

    // When user selects "not_available" in availability dropdown, auto-clear prices
    vAvailability.addEventListener("change", () => {
      if (vAvailability.value === "not_available") {
        vPriceJpy.value = "";
        vPriceEach.value = "";
        vVerificationStatus.value = "unavailable";
        actSpkCurrentJpy.textContent = "設定値: 価格不明 (国内流通なし)";
        actSpkCurrentJpy.style.color = "var(--accent-rose)";
        actSpkCPI.textContent = "CPI: ---";
        showToast("国内入手不可のため価格をクリア（価格不明）に設定しました");
      }
    });

    // Prev / Next buttons
    btnPrevSpeaker.addEventListener("click", () => navigateSpeaker(-1));
    btnNextSpeaker.addEventListener("click", () => navigateSpeaker(1));

    // Save buttons
    btnSaveOnly.addEventListener("click", () => saveVerification(false));
    btnSaveAndNext.addEventListener("click", () => saveVerification(true));

    // Keyboard shortcuts
    window.addEventListener("keydown", (e) => {
      // Only active if verification tab is visible
      const vView = document.getElementById("verificationView");
      if (!vView || vView.style.display === "none") return;

      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        saveVerification(true);
      } else if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
        e.preventDefault();
        saveVerification(false);
      } else if (e.altKey && e.key === "ArrowRight") {
        e.preventDefault();
        navigateSpeaker(1);
      } else if (e.altKey && e.key === "ArrowLeft") {
        e.preventDefault();
        navigateSpeaker(-1);
      }
    });
  }

  // Load verification statistics
  async function loadVerificationStats() {
    try {
      const res = await fetch("/api/verification/stats");
      if (!res.ok) throw new Error("Stats fetch failed");
      const stats = await res.json();
      vState.stats = stats;
      renderStats(stats);
    } catch (err) {
      // Fallback for static mode
      if (window.allStaticSpeakers) {
        calculateStaticStats(window.allStaticSpeakers);
      }
    }
  }

  function renderStats(stats) {
    statTotalCount.textContent = stats.total.toLocaleString();
    statUnverifiedCount.textContent = stats.unverified.toLocaleString();
    statNeedsReviewCount.textContent = stats.needs_review.toLocaleString();
    statVerifiedCount.textContent = stats.verified.toLocaleString();
    statUnavailableCount.textContent = stats.unavailable.toLocaleString();

    const pct = stats.progress_percent || 0;
    verifyProgressPct.textContent = `${pct.toFixed(1)}%`;
    verifyProgressBarFill.style.width = `${Math.min(100, Math.max(0, pct))}%`;

    if (tabUnverifiedBadge) {
      tabUnverifiedBadge.textContent = `${stats.unverified.toLocaleString()}件未検証`;
      if (stats.unverified === 0) {
        tabUnverifiedBadge.style.background = "rgba(16, 185, 129, 0.4)";
      }
    }
  }

  function calculateStaticStats(speakers) {
    const total = speakers.length;
    let verified = 0;
    let needs_review = 0;
    let unavailable = 0;
    let unverified = 0;

    speakers.forEach(s => {
      const st = s.verification_status || "unverified";
      if (st === "verified") verified++;
      else if (st === "needs_review") needs_review++;
      else if (st === "unavailable") unavailable++;
      else unverified++;
    });

    const progress = total > 0 ? Math.round(((verified + unavailable) / total) * 1000) / 10 : 0;
    renderStats({ total, verified, needs_review, unavailable, unverified, progress_percent: progress });
  }

  // Load brands for dropdown
  async function loadVerificationBrands() {
    try {
      const res = await fetch("/api/brands");
      if (!res.ok) return;
      const data = await res.json();
      verifierBrandSelect.innerHTML = '<option value="">全ブランド</option>' +
        data.brands.map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join("");
    } catch (_) {}
  }

  // Fetch speakers list
  async function fetchVerificationSpeakers(targetSpeakerId = null) {
    const params = new URLSearchParams({
      status: vState.filter,
      priority: vState.priority,
      brand: vState.brand,
      search: vState.search,
      limit: vState.limit,
      page: 1
    });

    try {
      const res = await fetch(`/api/verification/speakers?${params.toString()}`);
      if (!res.ok) throw new Error("Fetch failed");
      const data = await res.json();
      vState.items = data.items;
      vState.total = data.total;
      renderSidebarList(targetSpeakerId);
    } catch (err) {
      // Fallback to static mode
      if (window.allStaticSpeakers) {
        filterStaticSpeakers(targetSpeakerId);
      }
    }
  }

  function filterStaticSpeakers(targetSpeakerId = null) {
    let list = [...(window.allStaticSpeakers || [])];

    if (vState.filter !== "all") {
      list = list.filter(s => (s.verification_status || "unverified") === vState.filter);
    }
    if (vState.brand) {
      list = list.filter(s => s.brand === vState.brand);
    }
    if (vState.search) {
      const term = vState.search.toLowerCase();
      list = list.filter(s =>
        (s.brand && s.brand.toLowerCase().includes(term)) ||
        (s.model && s.model.toLowerCase().includes(term))
      );
    }

    if (vState.priority === "cpi_desc") {
      list.sort((a, b) => (b.cp_tone || 0) - (a.cp_tone || 0));
    } else if (vState.priority === "score_desc") {
      list.sort((a, b) => (b.score_tone || 0) - (a.score_tone || 0));
    } else if (vState.priority === "brand_asc") {
      list.sort((a, b) => a.brand.localeCompare(b.brand));
    }

    vState.items = list;
    vState.total = list.length;
    renderSidebarList(targetSpeakerId);
  }

  // Render left sidebar list
  function renderSidebarList(targetSpeakerId = null) {
    verifierListCount.textContent = `${vState.items.length.toLocaleString()} 件`;
    verifierItemsContainer.innerHTML = "";

    if (vState.items.length === 0) {
      verifierItemsContainer.innerHTML = `
        <div style="text-align: center; padding: 2rem 1rem; color: var(--text-muted); font-size: 0.85rem;">
          条件に合致するスピーカーがありません
        </div>
      `;
      vState.activeIndex = -1;
      vState.activeItem = null;
      updateActiveSpeakerUI(null);
      return;
    }

    vState.items.forEach((item, idx) => {
      const div = document.createElement("div");
      div.className = "verifier-item";
      div.dataset.index = idx;
      div.dataset.id = item.id;

      const vStatus = item.verification_status || "unverified";
      const statusBadge = getStatusBadgeHtml(vStatus);
      const isUnavailable = vStatus === "unavailable" || item.availability === "not_available";
      let priceText = "価格不明";
      let priceColor = "var(--text-muted)";
      if (isUnavailable) {
        priceText = "価格不明 (流通なし)";
        priceColor = "var(--accent-rose)";
      } else if (item.price_jpy) {
        priceText = `¥${Number(item.price_jpy).toLocaleString()}`;
        priceColor = "var(--accent-emerald)";
      } else if (item.effective_price_jpy) {
        priceText = `(約¥${Number(item.effective_price_jpy).toLocaleString()})`;
        priceColor = "var(--text-secondary)";
      }

      const cpiText = isUnavailable ? "---" : (item.cp_tone != null ? `CPI: ${Number(item.cp_tone).toFixed(2)}` : (item.cp_tone_est != null ? `参考CPI: ≈${Number(item.cp_tone_est).toFixed(2)}` : (item.score_tone != null ? `Tone: ${Number(item.score_tone).toFixed(1)}` : "")));

      div.innerHTML = `
        <div class="verifier-item-head">
          <span class="verifier-item-brand">${escapeHtml(item.brand)}</span>
          ${statusBadge}
        </div>
        <div class="verifier-item-model">${escapeHtml(item.model)}</div>
        <div class="verifier-item-footer">
          <span style="font-weight: 700; color: ${priceColor};">${priceText}</span>
          <span>${cpiText}</span>
        </div>
      `;

      div.addEventListener("click", () => {
        selectSpeakerByIndex(idx);
      });

      verifierItemsContainer.appendChild(div);
    });

    // Select target or default first item
    let targetIdx = 0;
    if (targetSpeakerId) {
      const found = vState.items.findIndex(s => s.id === targetSpeakerId);
      if (found !== -1) targetIdx = found;
    }
    selectSpeakerByIndex(targetIdx);
  }

  // Select speaker by index in items
  function selectSpeakerByIndex(idx) {
    if (idx < 0 || idx >= vState.items.length) return;

    vState.activeIndex = idx;
    vState.activeItem = vState.items[idx];

    // Highlight item in sidebar
    const allDivs = verifierItemsContainer.querySelectorAll(".verifier-item");
    allDivs.forEach((d, i) => {
      if (i === idx) {
        d.classList.add("active");
        d.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } else {
        d.classList.remove("active");
      }
    });

    verifierActiveIndex.textContent = `選択中: ${idx + 1} / ${vState.items.length}`;
    updateActiveSpeakerUI(vState.activeItem);
  }

  // Navigate next / prev
  function navigateSpeaker(direction) {
    const nextIdx = vState.activeIndex + direction;
    if (nextIdx >= 0 && nextIdx < vState.items.length) {
      selectSpeakerByIndex(nextIdx);
    } else {
      showToast(direction > 0 ? "最後のスピーカーです" : "先頭のスピーカーです");
    }
  }

  // Update active speaker workspace
  function updateActiveSpeakerUI(speaker) {
    if (!speaker) {
      actSpkTitle.textContent = "スピーカーを選択してください";
      actSpkBadgeContainer.innerHTML = "";
      return;
    }

    // Header info
    actSpkTitle.textContent = `${speaker.brand} ${speaker.model}`;
    actSpkPriceUsd.textContent = speaker.price_usd ? `USD: $${speaker.price_usd.toLocaleString()}` : "USD: -";
    actSpkToneScore.textContent = speaker.score_tone != null ? `Tone: ${speaker.score_tone.toFixed(2)}` : "Tone: -";
    actSpkF3.textContent = speaker.f3 ? `-3dB: ${speaker.f3.toFixed(0)}Hz` : "-3dB: -";

    const vStatus = speaker.verification_status || "unverified";
    const isUnavailable = vStatus === "unavailable" || speaker.availability === "not_available";

    if (isUnavailable) {
      actSpkCurrentJpy.textContent = "設定値: 価格不明 (国内流通なし)";
      actSpkCurrentJpy.style.color = "var(--accent-rose)";
      actSpkCPI.textContent = "CPI: ---";
    } else if (speaker.price_jpy) {
      actSpkCurrentJpy.textContent = `設定値: ¥${Number(speaker.price_jpy).toLocaleString()}`;
      actSpkCurrentJpy.style.color = "var(--accent-emerald)";
      actSpkCPI.textContent = speaker.cp_tone != null ? `CPI: ${speaker.cp_tone.toFixed(2)}` : (speaker.cp_tone_est != null ? `参考CPI: ≈${speaker.cp_tone_est.toFixed(2)}` : "CPI: -");
    } else if (speaker.effective_price_jpy) {
      actSpkCurrentJpy.textContent = `参考為替: 約¥${Number(speaker.effective_price_jpy).toLocaleString()}`;
      actSpkCurrentJpy.style.color = "var(--text-secondary)";
      actSpkCPI.textContent = speaker.cp_tone != null ? `CPI: ${speaker.cp_tone.toFixed(2)}` : (speaker.cp_tone_est != null ? `参考CPI: ≈${speaker.cp_tone_est.toFixed(2)}` : "CPI: -");
    } else {
      actSpkCurrentJpy.textContent = "設定値: 価格不明";
      actSpkCurrentJpy.style.color = "var(--text-muted)";
      actSpkCPI.textContent = "CPI: ---";
    }

    actSpkBadgeContainer.innerHTML = getStatusBadgeHtml(vStatus, true);

    // Search Assistant
    const defaultKeyword = `${speaker.brand} ${speaker.model} ペア 価格`;
    const activeKeyword = speaker.search_keyword || defaultKeyword;
    assistantKeywordInput.value = activeKeyword;
    updateSearchLinks(activeKeyword);

    // Generate Keyword Chips
    renderKeywordChips(speaker);

    // Fill Input Form
    vSpeakerId.value = speaker.id;
    vSourceUrl.value = speaker.source_url || "";
    vSearchKeyword.value = activeKeyword;
    vSourceName.value = speaker.source_name || (isUnavailable ? "国内流通なし確認" : (speaker.is_manual_override ? "手動確認" : ""));
    
    if (isUnavailable) {
      vPriceEach.value = "";
      vPriceJpy.value = "";
      vAvailability.value = "not_available";
    } else {
      vPriceEach.value = speaker.price_each || "";
      vPriceJpy.value = speaker.price_jpy || speaker.effective_price_jpy || "";
      vAvailability.value = speaker.availability || "domestic_in_stock";
    }

    vPriceType.value = speaker.price_type || "pair";
    vVerificationStatus.value = vStatus;
    vConfidenceLevel.value = speaker.confidence_level || (vStatus === "verified" || vStatus === "unavailable" ? "high" : "low");
    vNotes.value = speaker.notes || (isUnavailable ? "日本国内での正規流通・市販なし" : "");
  }

  // Keyword Chips rendering
  function renderKeywordChips(speaker) {
    keywordChipsContainer.innerHTML = "";
    const suggestions = [
      `${speaker.brand} ${speaker.model} 実売 価格`,
      `${speaker.brand} ${speaker.model} ペア 価格`,
      `${speaker.brand} ${speaker.model} サウンドハウス`,
      `${speaker.brand} ${speaker.model} 価格.com`,
      `${speaker.brand} ${speaker.model} Amazon`,
      `${speaker.brand} ${speaker.model} 国内定価`
    ];

    suggestions.forEach(kw => {
      const chip = document.createElement("span");
      chip.className = "suggestion-chip";
      chip.textContent = kw;
      chip.addEventListener("click", () => {
        assistantKeywordInput.value = kw;
        vSearchKeyword.value = kw;
        updateSearchLinks(kw);
        copySearchKeyword();
      });
      keywordChipsContainer.appendChild(chip);
    });
  }

  // Update Instant Search URLs
  function updateSearchLinks(keyword) {
    const q = encodeURIComponent(keyword);
    btnSearchGoogle.href = `https://www.google.com/search?q=${q}`;
    btnSearchKakaku.href = `https://kakaku.com/search_results/${q}/`;
    btnSearchSoundhouse.href = `https://www.soundhouse.co.jp/search/index/?search_type=s_all&s_category_cd=&i_type=a&s_key=${q}`;
    btnSearchAmazon.href = `https://www.amazon.co.jp/s?k=${q}`;
    btnSearchYodobashi.href = `https://www.yodobashi.com/?word=${q}`;
  }

  // Copy keyword to clipboard
  async function copySearchKeyword() {
    const kw = assistantKeywordInput.value.trim();
    if (!kw) return;

    try {
      await navigator.clipboard.writeText(kw);
      btnCopyKeyword.classList.add("copied");
      copyIcon.textContent = "✓";
      copyText.textContent = "コピー完了！";
      showToast(`「${kw}」をコピーしました`);
      setTimeout(() => {
        btnCopyKeyword.classList.remove("copied");
        copyIcon.textContent = "📋";
        copyText.textContent = "コピー";
      }, 1500);
    } catch (_) {
      // Fallback for older browsers
      assistantKeywordInput.select();
      document.execCommand("copy");
      showToast("検索ワードをコピーしました");
    }
  }

  // Save verification result
  async function saveVerification(andNext = false) {
    if (window.isStaticMode) {
      alert("【閲覧専用モード】\nCloudflare Pages版ではブラウザからの直接DB保存は無効化されています。\n自宅Linuxのローカル環境で行ってください。");
      return;
    }

    const spkId = parseInt(vSpeakerId.value, 10);
    if (!spkId) return;

    const isUnavailable = vVerificationStatus.value === "unavailable" || vAvailability.value === "not_available";

    const payload = {
      speaker_id: spkId,
      price_jpy: isUnavailable ? null : (vPriceJpy.value ? parseInt(vPriceJpy.value, 10) : null),
      price_type: vPriceType.value,
      price_each: isUnavailable ? null : (vPriceEach.value ? parseInt(vPriceEach.value, 10) : null),
      availability: isUnavailable ? "not_available" : vAvailability.value,
      source_name: vSourceName.value.trim() || (isUnavailable ? "国内流通なし確認" : "手動確認"),
      source_url: vSourceUrl.value.trim(),
      search_keyword: vSearchKeyword.value.trim(),
      verification_status: vVerificationStatus.value,
      confidence_level: vConfidenceLevel.value,
      notes: vNotes.value.trim() || (isUnavailable ? "日本国内での正規流通・市販なし" : ""),
      is_manual_override: true
    };

    try {
      const res = await fetch("/api/verification/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const resData = await res.json();

      // Update in-memory state for the saved speaker
      const savedItem = vState.items.find(s => s.id === spkId) || vState.activeItem;
      if (savedItem) {
        savedItem.price_jpy = payload.price_jpy;
        savedItem.price_type = payload.price_type;
        savedItem.price_each = payload.price_each;
        savedItem.effective_price_jpy = isUnavailable ? null : payload.price_jpy;
        savedItem.availability = payload.availability;
        savedItem.source_name = payload.source_name;
        savedItem.source_url = payload.source_url;
        savedItem.search_keyword = payload.search_keyword;
        savedItem.verification_status = payload.verification_status;
        savedItem.confidence_level = payload.confidence_level;
        savedItem.notes = payload.notes;
        savedItem.is_manual_override = 1;
        if (isUnavailable) {
          savedItem.cp_tone = null;
        } else if (resData && resData.cp_tone !== undefined && resData.cp_tone !== null) {
          savedItem.cp_tone = resData.cp_tone;
        }
        // Update sidebar item in DOM immediately!
        updateSidebarItemDOM(savedItem);
      }

      showToast(`「${actSpkTitle.textContent}」の検証情報を保存しました ✓`);

      // Update stats and badge
      loadVerificationStats();

      // Refresh main table if present
      if (window.refreshApp) {
        window.refreshApp();
      }

      if (andNext) {
        navigateSpeaker(1);
      } else {
        // Re-render current active item
        if (savedItem && vState.activeItem && vState.activeItem.id === spkId) {
          updateActiveSpeakerUI(savedItem);
        }
      }
    } catch (err) {
      alert("保存に失敗しました: " + err.message);
    }
  }

  // Update a single item in the sidebar DOM
  function updateSidebarItemDOM(item) {
    if (!item || !item.id) return;
    const div = verifierItemsContainer.querySelector(`.verifier-item[data-id="${item.id}"]`);
    if (!div) return;

    const vStatus = item.verification_status || "unverified";
    const statusBadge = getStatusBadgeHtml(vStatus);

    const isUnavailable = vStatus === "unavailable" || item.availability === "not_available";
    let priceText = "価格不明";
    let priceColor = "var(--text-muted)";
    if (isUnavailable) {
      priceText = "価格不明 (流通なし)";
      priceColor = "var(--accent-rose)";
    } else if (item.price_jpy) {
      priceText = `¥${Number(item.price_jpy).toLocaleString()}`;
      priceColor = "var(--accent-emerald)";
    } else if (item.effective_price_jpy) {
      priceText = `(約¥${Number(item.effective_price_jpy).toLocaleString()})`;
      priceColor = "var(--text-secondary)";
    }

    const cpiText = isUnavailable ? "---" : (item.cp_tone != null
      ? `CPI: ${Number(item.cp_tone).toFixed(2)}`
      : (item.cp_tone_est != null ? `参考CPI: ≈${Number(item.cp_tone_est).toFixed(2)}` : (item.score_tone != null ? `Tone: ${Number(item.score_tone).toFixed(1)}` : "")));

    div.innerHTML = `
      <div class="verifier-item-head">
        <span class="verifier-item-brand">${escapeHtml(item.brand)}</span>
        ${statusBadge}
      </div>
      <div class="verifier-item-model">${escapeHtml(item.model)}</div>
      <div class="verifier-item-footer">
        <span style="font-weight: 700; color: ${priceColor};">${priceText}</span>
        <span>${cpiText}</span>
      </div>
    `;
  }

  // Toast notification
  function showToast(message) {
    const existing = document.querySelector(".toast-msg");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast-msg";
    toast.innerHTML = `<span>⚡</span> <span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = "opacity 0.4s ease";
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 400);
    }, 2000);
  }

  // Helpers
  function getStatusBadgeHtml(status, large = false) {
    const style = large ? 'style="font-size: 0.85rem; padding: 4px 10px;"' : '';
    switch (status) {
      case "verified":
        return `<span class="status-badge verified" ${style}>🟢 検証済み</span>`;
      case "needs_review":
        return `<span class="status-badge needs_review" ${style}>🟡 要再確認</span>`;
      case "unavailable":
        return `<span class="status-badge unavailable" ${style}>🚫 国内流通なし</span>`;
      case "unverified":
      default:
        return `<span class="status-badge unverified" ${style}>🔴 未検証</span>`;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Public API
  window.openVerificationForSpeaker = function (speakerId) {
    // Switch to verification tab
    const tabVerif = document.getElementById("tabBtnVerification");
    if (tabVerif) tabVerif.click();

    // Fetch and select speaker
    fetchVerificationSpeakers(speakerId);
  };

  // Initialize on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initVerificationStudio);
  } else {
    initVerificationStudio();
  }

})();

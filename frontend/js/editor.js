// Modal for Editing Japanese Price & Availability

const editModal = document.getElementById("editModal");
const editForm = document.getElementById("editForm");
const closeModalBtn = document.getElementById("closeModalBtn");
const cancelModalBtn = document.getElementById("cancelModalBtn");

const modalSpeakerName = document.getElementById("modalSpeakerName");
const editSpeakerId = document.getElementById("editSpeakerId");
const editPriceJpy = document.getElementById("editPriceJpy");
const editPriceType = document.getElementById("editPriceType");
const editAvailability = document.getElementById("editAvailability");
const editSourceName = document.getElementById("editSourceName");
const editSourceUrl = document.getElementById("editSourceUrl");
const editNotes = document.getElementById("editNotes");
const editIsManual = document.getElementById("editIsManual");

const quickUnavailableBtn = document.getElementById("quickUnavailableBtn");
if (quickUnavailableBtn) {
  quickUnavailableBtn.addEventListener("click", () => {
    editAvailability.value = "not_available";
    editPriceJpy.value = "";
    editNotes.value = "日本国内での正規流通・市販なし（入手困難）";
    editIsManual.checked = true;
  });
}

editAvailability.addEventListener("change", () => {
  if (editAvailability.value === "not_available") {
    editPriceJpy.value = "";
    if (!editNotes.value) {
      editNotes.value = "日本国内での正規流通・市販なし（入手困難）";
    }
  }
});

function openEditModal(speaker) {
  const isUnavailable = speaker.availability === "not_available" || speaker.verification_status === "unavailable";
  modalSpeakerName.textContent = `${speaker.brand} ${speaker.model} - 日本市場データ編集`;
  editSpeakerId.value = speaker.id;
  editPriceJpy.value = isUnavailable ? "" : (speaker.price_jpy || speaker.effective_price_jpy || "");
  editPriceType.value = speaker.price_type || "pair";
  editAvailability.value = speaker.availability || "unconfirmed";
  editSourceName.value = speaker.source_name || (isUnavailable ? "国内流通なし確認" : "");
  editSourceUrl.value = speaker.source_url || "";
  editNotes.value = speaker.notes || (isUnavailable ? "日本国内での正規流通・市販なし" : "");
  editIsManual.checked = speaker.is_manual_override === 1 || true;

  editModal.classList.add("active");
}

function closeEditModal() {
  editModal.classList.remove("active");
}

closeModalBtn.addEventListener("click", closeEditModal);
cancelModalBtn.addEventListener("click", closeEditModal);
editModal.addEventListener("click", (e) => {
  if (e.target === editModal) closeEditModal();
});

editForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (window.isStaticMode) {
    alert("【閲覧専用モード】\nCloudflare Pages版ではブラウザからの直接DB保存は無効化されています。\n価格や入手性の手動修正は、自宅Linuxのローカル管理画面で行い、静的エクスポートを行ってください。");
    closeEditModal();
    return;
  }

  const isUnavailable = editAvailability.value === "not_available";

  const payload = {
    speaker_id: parseInt(editSpeakerId.value),
    price_jpy: isUnavailable ? null : (parseInt(editPriceJpy.value) || null),
    price_type: editPriceType.value,
    availability: editAvailability.value,
    source_name: editSourceName.value.trim() || (isUnavailable ? "国内流通なし確認" : ""),
    source_url: editSourceUrl.value.trim(),
    notes: editNotes.value.trim(),
    is_manual_override: editIsManual.checked
  };

  try {
    const res = await fetch("/api/speakers/update_market", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Update failed");

    closeEditModal();
    // Refresh table and stats
    if (window.refreshApp) {
      window.refreshApp();
    }
  } catch (err) {
    alert("更新に失敗しました: " + err.message);
  }
});

window.openEditModal = openEditModal;

/* =========================
   MODAL
========================= */
let aiSummaryLoadingInterval = null;

function renderAiSummaryLoading() {
    const container = document.getElementById("modalAiSummary");
    if (!container) return;

    if (aiSummaryLoadingInterval) {
        clearInterval(aiSummaryLoadingInterval);
        aiSummaryLoadingInterval = null;
    }

    container.classList.remove("d-none");

    container.innerHTML = `
        <div class="alert alert-secondary mt-3 mb-0 small">
            <div class="d-flex align-items-center gap-2 mb-1">
                <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
                <span id="ai-loading-text">Initializing...</span>
            </div>
        </div>
    `;

    const steps = [
        "Analyzing dealer data...",
        "Evaluating ratings...",
        "Checking reliability...",
        "Generating summary..."
    ];

    let i = 0;
    const textEl = document.getElementById("ai-loading-text");
    if (!textEl) return;

    aiSummaryLoadingInterval = setInterval(() => {
        if (!document.body.contains(textEl)) {
            clearInterval(aiSummaryLoadingInterval);
            aiSummaryLoadingInterval = null;
            return;
        }

        if (i < steps.length) {
            textEl.textContent = steps[i];
            i++;
        } else {
            clearInterval(aiSummaryLoadingInterval);
            aiSummaryLoadingInterval = null;
        }
    }, 800);
}

function resetAiSummaryButton() {
    const summaryBtn = document.getElementById("loadSummaryBtn");
    if (!summaryBtn) return;

    summaryBtn.disabled = false;
    summaryBtn.textContent = "? Generate AI summary";
    summaryBtn.classList.remove("d-none");
}

function bindAiSummaryButton(card, placeId, baseData) {
    const summaryBtn = document.getElementById("loadSummaryBtn");
    if (!summaryBtn) return;

    summaryBtn.onclick = null;
    summaryBtn.disabled = false;
    summaryBtn.textContent = "✨ Generate AI summary";
    summaryBtn.classList.remove("d-none");

    summaryBtn.onclick = async function () {
        summaryBtn.disabled = true;
        summaryBtn.textContent = "Generating...";

        renderAiSummaryLoading();

        try {
            const response = await fetch(`/dealer/${placeId}/ai-summary/`, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                throw new Error("AI summary request failed");
            }

            const ai = await response.json();

            card.dataset.dealerAiStatus = ai.status || "failed";
            card.dataset.dealerAiSummary = ai.summary || "";
            card.dataset.dealerAiPros = JSON.stringify(ai.pros || []);
            card.dataset.dealerAiCons = JSON.stringify(ai.cons || []);

            renderAiSummary({
                ...baseData,
                ai_status: ai.status || "failed",
                ai_summary: ai.summary || "",
                ai_pros: ai.pros || [],
                ai_cons: ai.cons || [],
            });

            if ((ai.status || "") === "done") {
                summaryBtn.classList.add("d-none");
                return;
            }

            if ((ai.status || "") === "pending") {
                summaryBtn.disabled = false;
                summaryBtn.textContent = "Refresh summary";
                return;
            }

            summaryBtn.disabled = false;
            summaryBtn.textContent = "Try again";
        } catch (error) {
            renderAiSummary({
                ...baseData,
                ai_status: "failed",
                ai_summary: "",
                ai_pros: [],
                ai_cons: [],
            });

            summaryBtn.disabled = false;
            summaryBtn.textContent = "Try again";
        }
    };
}

function bindModalFavoriteButton(card) {
    const favoriteBtn = document.getElementById("modalFavoriteBtn");
    if (!favoriteBtn) return;

    const placeId = card.dataset.dealerPlaceId || "";
    const name = card.dataset.dealerName || "";
    const address = card.dataset.dealerAddress || "";
    const rating = card.dataset.dealerRating || "";
    const phone = card.dataset.dealerPhone || "";
    const website = card.dataset.dealerWebsite || "";
    const isFavorite = card.dataset.dealerIsFavorite === "1";

    favoriteBtn.onclick = null;
    favoriteBtn.disabled = false;

    if (isFavorite) {
        favoriteBtn.className = "btn btn-outline-danger flex-grow-1";
        favoriteBtn.textContent = "✖ Remove from favorites";

        favoriteBtn.onclick = function () {
            removeFavorite(placeId);
        };
    } else {
        favoriteBtn.className = "btn btn-outline-secondary flex-grow-1";
        favoriteBtn.textContent = "☆ Add to favorites";

        favoriteBtn.onclick = function () {
            addFavorite(favoriteBtn, {
                place_id: placeId,
                name: name,
                address: address,
                rating: rating,
                phone: phone,
                website: website,
                lat: card.dataset.dealerLat || "",
                lng: card.dataset.dealerLng || "",
            });
        };
    }
}

function parseJsonArray(value) {
    if (!value) {
        return [];
    }

    try {
        return JSON.parse(value);
    } catch {
        return [];
    }
}

function openDealerModal(card) {
    const modalEl = document.getElementById("dealerModal");
    const nameEl = document.getElementById("modalDealerName");
    const infoEl = document.getElementById("modalInfo");
    const mapEl = document.getElementById("modalMap");
    const routeBtn = document.getElementById("modalRouteBtn");
    const summaryEl = document.getElementById("modalAiSummary");

const data = {
    name: card.dataset.dealerName || "",
    address: card.dataset.dealerAddress || "",
    phone: card.dataset.dealerPhone || "",
    website: card.dataset.dealerWebsite || "",
    rating: card.dataset.dealerRating || "",
    distance: card.dataset.dealerDistance || "",
    lat: card.dataset.dealerLat,
    lng: card.dataset.dealerLng,
    ai_summary: card.dataset.dealerAiSummary || "",
    ai_status: card.dataset.dealerAiStatus || "pending",
    ai_pros: parseJsonArray(card.dataset.dealerAiPros),
    ai_cons: parseJsonArray(card.dataset.dealerAiCons),
};

    nameEl.textContent = data.name;
    infoEl.replaceChildren();

    appendInfoRow(infoEl, "Address", data.address);
    appendInfoRow(infoEl, "Phone", data.phone);

    const safeWebsite = toSafeExternalUrl(data.website);
    if (safeWebsite) {
        appendInfoRow(infoEl, "Website", safeWebsite, { href: safeWebsite });
    }

    appendInfoRow(infoEl, "Rating", data.rating);
    appendInfoRow(infoEl, "Distance", data.distance ? `${data.distance} km` : "");

    if (isFiniteCoordinate(data.lat, -90, 90) && isFiniteCoordinate(data.lng, -180, 180)) {
        mapEl.src = `https://maps.google.com/maps?q=${data.lat},${data.lng}&z=15&output=embed`;
        routeBtn.href = `https://www.google.com/maps/dir/?api=1&destination=${data.lat},${data.lng}`;
    } else {
        mapEl.src = "";
        routeBtn.removeAttribute("href");
    }

    bindModalFavoriteButton(card);

    if (summaryEl) {
        summaryEl.classList.add("d-none");
        summaryEl.innerHTML = "";
    }

    const placeId = card.dataset.dealerPlaceId || "";

    resetAiSummaryButton();

    if (data.ai_status === "done" && data.ai_summary) {
        renderAiSummary(data);

        const summaryBtn = document.getElementById("loadSummaryBtn");
        if (summaryBtn) {
            summaryBtn.classList.add("d-none");
        }
    } else {
        bindAiSummaryButton(card, placeId, data);
    }

    bootstrap.Modal.getOrCreateInstance(modalEl).show();
}


/* =========================
   CLICK HANDLER
========================= */
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-open-dealer-modal");
    if (!btn) return;
    openDealerModal(btn);
});

/* =========================
   AI SUMMARY
========================= */
function renderAiSummary(data) {
    const container = document.getElementById("modalAiSummary");
    if (!container) return;

    const status = data.ai_status;
    const summary = data.ai_summary;
    const pros = Array.isArray(data.ai_pros) ? data.ai_pros : [];
    const cons = Array.isArray(data.ai_cons) ? data.ai_cons : [];

    container.classList.add("d-none");
    container.innerHTML = "";

    if (status === "pending") {
        container.classList.remove("d-none");
        container.innerHTML = `
            <div class="alert alert-secondary mt-3 mb-0 small">
                AI summary is being generated...
            </div>
        `;
        return;
    }

    if (status === "done" && summary) {
        const prosHtml = pros.map((item) => `
            <div class="ai-summary-point ai-summary-point--pros">
                <span class="ai-summary-point__icon">+</span>
                <span>${escapeHtml(item)}</span>
            </div>
        `).join("");

        const consHtml = cons.map((item) => `
            <div class="ai-summary-point ai-summary-point--cons">
                <span class="ai-summary-point__icon">!</span>
                <span>${escapeHtml(item)}</span>
            </div>
        `).join("");

        container.classList.remove("d-none");
        container.innerHTML = `
            <div class="surface-card-muted p-3 mt-3">
                <div class="fw-semibold mb-2">AI summary (based on reviews)</div>
                <p class="small text-secondary mb-3">${escapeHtml(summary)}</p>

                ${pros.length ? `
                    <div class="ai-summary-list mb-2">
                        ${prosHtml}
                    </div>
                ` : ""}

                ${cons.length ? `
                    <div class="ai-summary-list">
                        ${consHtml}
                    </div>
                ` : ""}
            </div>
        `;
        return;
    }

    if (status === "failed") {
        container.classList.remove("d-none");
        container.innerHTML = `
            <div class="alert alert-warning mt-3 mb-0 small">
                AI summary unavailable
            </div>
        `;
    }
}
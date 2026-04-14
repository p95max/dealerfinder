let aiSummaryLoadingInterval = null;

/* =========================
   HELPERS
========================= */
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

function appendInfoRow(container, label, value, options = {}) {
    if (!container || !value) return;

    const row = document.createElement("div");
    row.className = "mb-2";

    const strong = document.createElement("strong");
    strong.textContent = `${label}: `;
    row.appendChild(strong);

    if (options.href) {
        const link = document.createElement("a");
        link.href = options.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = value;
        row.appendChild(link);
    } else {
        row.appendChild(document.createTextNode(value));
    }

    container.appendChild(row);
}

async function pollAiSummary(placeId, baseData, card, summaryBtn) {
    const maxAttempts = 15;
    let attempts = 0;
    const modalEl = document.getElementById("dealerModal");

    while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 2000));

        if (
            !modalEl ||
            modalEl.dataset.placeId !== placeId ||
            !modalEl.classList.contains("show")
        ) {
            return;
        }

        try {
            const response = await fetch(`/dealer/${placeId}/ai-summary/`, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (!response.ok) {
                break;
            }

            const ai = await response.json();

            card.dataset.dealerAiStatus = ai.status || "failed";
            card.dataset.dealerAiSummary = ai.summary || "";
            card.dataset.dealerAiPros = JSON.stringify(ai.pros || []);
            card.dataset.dealerAiCons = JSON.stringify(ai.cons || []);
            card.dataset.dealerAiErrorCode = ai.error_code || "";
            card.dataset.dealerAiMessage = ai.message || ai.error || "";

            renderAiSummary({
                ...baseData,
                ai_status: ai.status || "failed",
                ai_summary: ai.summary || "",
                ai_pros: ai.pros || [],
                ai_cons: ai.cons || [],
                ai_error_code: ai.error_code || "",
                ai_message: ai.message || ai.error || "",
            });

            if (ai.status === "done") {
                summaryBtn.classList.add("d-none");
                return;
            }

            if (ai.status === "failed") {
                summaryBtn.disabled = false;
                summaryBtn.textContent = "Try again";
                return;
            }
        } catch (error) {
            console.error("Polling failed", error);
            break;
        }

        attempts += 1;
    }

    summaryBtn.disabled = false;
    summaryBtn.textContent = "Try again";
}

/* =========================
   AI SUMMARY
========================= */
function renderAiSummary(data) {
    const container = document.getElementById("modalAiSummary");
    if (!container) return;

    const status = data.ai_status;
    const summary = data.ai_summary;
    const errorCode = data.ai_error_code || "";
    const message = data.ai_message || data.ai_error || "AI summary unavailable";
    const pros = Array.isArray(data.ai_pros) ? data.ai_pros : [];
    const cons = Array.isArray(data.ai_cons) ? data.ai_cons : [];

    container.classList.add("d-none");
    container.innerHTML = "";

    if (status === "pending") {
        container.classList.remove("d-none");
        container.innerHTML = `
            <div class="alert alert-secondary mt-3 mb-0 small d-flex align-items-center gap-2">
                <div class="spinner-border spinner-border-sm" role="status"></div>
                <span>AI summary is being prepared. This may take a few seconds.</span>
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
                <div class="fw-semibold mb-2">Based on Google Maps reviews</div>
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
                ${escapeHtml(message)}
            </div>
        `;
    }
}
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

    summaryBtn.disabled = true;
    summaryBtn.textContent = "✨ Analyze this dealer";
    summaryBtn.classList.remove("d-none");
}
function initAiConsent(data) {
    const checkbox = document.getElementById("aiConsentCheckbox");
    const button = document.getElementById("loadSummaryBtn");
    const summaryContainer = document.getElementById("modalAiSummary");

    if (!checkbox || !button || !summaryContainer) return;

    const STORAGE_KEY = "aiConsentAccepted";

    checkbox.onchange = null;

    const alreadyAccepted = sessionStorage.getItem(STORAGE_KEY) === "1";

    if (alreadyAccepted) {
        checkbox.checked = true;
        button.disabled = false;

        if (data.ai_status === "done" && data.ai_summary) {
            button.classList.add("d-none");
            renderAiSummary(data);
        } else {
            button.classList.remove("d-none");
        }

        return;
    }

    checkbox.checked = false;

    summaryContainer.classList.add("d-none");
    summaryContainer.innerHTML = "";

    button.disabled = true;

    checkbox.onchange = () => {
        const accepted = checkbox.checked;

        if (!accepted) {
            button.disabled = true;

            summaryContainer.classList.add("d-none");
            summaryContainer.innerHTML = "";
            return;
        }

        sessionStorage.setItem(STORAGE_KEY, "1");

        if (data.ai_status === "done" && data.ai_summary) {
            button.classList.add("d-none");
            renderAiSummary(data);
            return;
        }

        button.classList.remove("d-none");
        button.disabled = false;
    };
}

function bindAiSummaryButton(card, placeId, baseData) {
    const summaryBtn = document.getElementById("loadSummaryBtn");
    if (!summaryBtn) return;

    summaryBtn.onclick = null;

    const checkbox = document.getElementById("aiConsentCheckbox");
    summaryBtn.disabled = !(checkbox && checkbox.checked);

    summaryBtn.textContent = "✨ Analyze this dealer";
    summaryBtn.classList.remove("d-none");

    summaryBtn.onclick = async function () {
        summaryBtn.disabled = true;
        summaryBtn.textContent = "Generating...";

        renderAiSummaryLoading();

        try {
            const response = await fetch(`/dealer/${placeId}/ai-summary/generate/`, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCsrfToken(),
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
            card.dataset.dealerAiErrorCode = ai.error_code || "";
            card.dataset.dealerAiMessage = ai.message || ai.error || "";

            renderAiSummary({
                ...baseData,
                ai_status: ai.status || "failed",
                ai_summary: ai.summary || "",
                ai_pros: ai.pros || [],
                ai_cons: ai.cons || [],
                ai_error_code: ai.error_code || "",
                ai_message: ai.message || ai.error || "",
            });

            if (window.isAuthenticated && typeof refreshQuotaCounters === "function") {
                refreshQuotaCounters();
            }

            if ((ai.status || "") === "done") {
                summaryBtn.classList.add("d-none");
                return;
            }

            if ((ai.status || "") === "pending") {
                summaryBtn.disabled = true;
                summaryBtn.textContent = "Preparing...";
                pollAiSummary(placeId, baseData, card, summaryBtn);
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
                ai_error_code: "",
                ai_message: "AI summary unavailable.",
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
        favoriteBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg"
                     width="16"
                     height="16"
                     fill="currentColor"
                     viewBox="0 0 16 16"
                     aria-hidden="true">
                    <path d="M2 2.5A1.5 1.5 0 0 1 3.5 1h9A1.5 1.5 0 0 1 14 2.5v12a.5.5 0 0 1-.79.407L8 11.101l-5.21 3.806A.5.5 0 0 1 2 14.5v-12z"/>
                </svg>
                <span>Add to favorites</span>
            `;

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

/* =========================
   SHARE BUTTON
========================= */

function buildDealerShareData(modalEl) {
    const title =
        document.getElementById("modalDealerName")?.textContent?.trim() || "Dealer";

    const placeId = modalEl?.dataset.placeId || "";
    const shareUrl = new URL(window.location.href);

    if (placeId) {
        shareUrl.searchParams.set("dealer", placeId);
    }

    return {
        title,
        url: shareUrl.toString(),
        text: `Take a look at this dealer: ${title}`,
    };
}

function initShareButtons(modalEl) {
    const shareBtn = document.getElementById("modalShareBtn");
    const shareMenu = document.getElementById("modalShareMenu");
    const copyBtn = document.getElementById("shareCopyBtn");
    const telegramBtn = document.getElementById("shareTelegramBtn");
    const whatsappBtn = document.getElementById("shareWhatsappBtn");
    const emailBtn = document.getElementById("shareEmailBtn");

    if (!shareBtn || !shareMenu || !modalEl) {
        return;
    }

    const { title, url, text } = buildDealerShareData(modalEl);

    if (telegramBtn) {
        telegramBtn.href =
            `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
    }

    if (whatsappBtn) {
        whatsappBtn.href =
            `https://wa.me/?text=${encodeURIComponent(text + " " + url)}`;
    }

    if (emailBtn) {
        emailBtn.href =
            `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(text + "\n\n" + url)}`;
    }

    if (copyBtn) {
        copyBtn.onclick = async () => {
            try {
                await navigator.clipboard.writeText(url);
                alert("Link copied");
            } catch {
                window.prompt("Copy this link:", url);
            }
        };
    }

    shareBtn.onclick = async (event) => {
        const canUseNativeShare =
            typeof navigator.share === "function" &&
            typeof navigator.canShare === "function"
                ? navigator.canShare({ title, text, url })
                : typeof navigator.share === "function";

        if (!canUseNativeShare) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        try {
            await navigator.share({ title, text, url });
        } catch (error) {
            // user canceled — do nothing
            console.warn("Share canceled or failed:", error);
        }
    };
}

/* =========================
   MODAL/ORCHESTRATOR
========================= */
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
        ai_error_code: card.dataset.dealerAiErrorCode || "",
        ai_message: card.dataset.dealerAiMessage || "",
    };

    nameEl.textContent = data.name;
    infoEl.replaceChildren();

    appendInfoRow(infoEl, "Address", data.address);
    appendInfoRow(infoEl, "Phone", data.phone);

    function formatWebsiteLabel(url) {
        try {
            const u = new URL(url);
            return u.hostname.replace("www.", "");
        } catch {
            return "Website";
        }
    }

    const safeWebsite = toSafeExternalUrl(data.website);
    if (safeWebsite) {
            appendInfoRow(
                infoEl,
                "Website",
                formatWebsiteLabel(safeWebsite),
                { href: safeWebsite }
            );
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


    modalEl.dataset.placeId = placeId;

    initShareButtons(modalEl);
    resetAiSummaryButton();
    bindAiSummaryButton(card, placeId, data);
    initAiConsent(data);

    bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

document.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-open-dealer-modal");
    if (!btn) return;
    openDealerModal(btn);
});




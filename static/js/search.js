document.addEventListener("DOMContentLoaded", () => {
    initLocationSearchForm();
    initCityAutocomplete();
});


/* =========================
   GEOLOCATION
========================= */
function initLocationSearchForm() {
    const form = document.getElementById("dealerSearchForm");
    const locationCheckbox = document.getElementById("use_my_location");
    const latInput = document.getElementById("user_lat");
    const lngInput = document.getElementById("user_lng");
    const searchButton = form?.querySelector('button[type="submit"]');
    const locationHelp = document.getElementById("locationHelp");

    if (!form || !locationCheckbox || !latInput || !lngInput || !searchButton) {
        return;
    }

    let geoRequestInProgress = false;

    function setMessage(msg, isError = false) {
        if (!locationHelp) return;
        locationHelp.textContent = msg;
        locationHelp.classList.toggle("text-danger", isError);
    }

    function clearCoords() {
        latInput.value = "";
        lngInput.value = "";
    }

    function hasCoords() {
        return latInput.value && lngInput.value;
    }

    function setLoading(isLoading) {
        geoRequestInProgress = isLoading;
        searchButton.disabled = isLoading;

        if (isLoading) {
            searchButton.dataset.originalText = searchButton.textContent;
            searchButton.textContent = "Detecting location...";
        } else if (searchButton.dataset.originalText) {
            searchButton.textContent = searchButton.dataset.originalText;
        }
    }

    function requestLocation(cb = null) {
        if (!navigator.geolocation) {
            setMessage("Geolocation not supported", true);
            locationCheckbox.checked = false;
            clearCoords();
            return;
        }

        setLoading(true);
        setMessage("Detecting your location...");

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                latInput.value = pos.coords.latitude;
                lngInput.value = pos.coords.longitude;

                setLoading(false);
                setMessage("Location detected");

                if (cb) cb();
            },
            () => {
                clearCoords();
                locationCheckbox.checked = false;
                setLoading(false);
                setMessage("Location failed", true);
            },
            { timeout: 10000 }
        );
    }

    locationCheckbox.addEventListener("change", () => {
        if (!locationCheckbox.checked) {
            clearCoords();
            setMessage("Location is optional");
            return;
        }
        requestLocation();
    });

    form.addEventListener("submit", (e) => {
        if (!locationCheckbox.checked) return;

        if (geoRequestInProgress) {
            e.preventDefault();
            return;
        }

        if (!hasCoords()) {
            e.preventDefault();
            requestLocation(() => form.submit());
        }
    });
}


/* =========================
   AUTOCOMPLETE
========================= */
function initCityAutocomplete() {
    fetch("/static/data/cities_de.json")
        .then(r => r.json())
        .then(cities => {
            const input = document.getElementById("city");
            const datalist = document.getElementById("cities-list");
            if (!input || !datalist) return;

            input.addEventListener("input", () => {
                const val = input.value.toLowerCase().trim();
                datalist.innerHTML = "";

                if (val.length < 2) return;

                cities
                    .filter(c => c.toLowerCase().startsWith(val))
                    .slice(0, 10)
                    .forEach(c => {
                        const opt = document.createElement("option");
                        opt.value = c;
                        datalist.appendChild(opt);
                    });
            });
        })
        .catch(() => {});
}


/* =========================
   HELPERS
========================= */
function isFiniteCoordinate(value, min, max) {
    const num = Number(value);
    return Number.isFinite(num) && num >= min && num <= max;
}

function toSafeExternalUrl(value) {
    try {
        const url = new URL(value);
        return ["http:", "https:"].includes(url.protocol) ? url.href : null;
    } catch {
        return null;
    }
}

function appendInfoRow(container, label, value, options = {}) {
    if (!value) return;

    const row = document.createElement("div");

    const strong = document.createElement("b");
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

function escapeHtml(str) {
    return String(str)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}


/* =========================
   AI SUMMARY
========================= */
function renderAiSummary(data) {
    const container = document.getElementById("modalAiSummary");
    if (!container) return;

    const status = data.ai_status;
    const summary = data.ai_summary;

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
        container.classList.remove("d-none");
        container.innerHTML = `
            <div class="surface-card-muted p-3 mt-3">
                <div class="fw-semibold mb-2">AI review summary</div>
                <p class="small text-secondary mb-2">${escapeHtml(summary)}</p>
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
    summaryBtn.textContent = "? Generate AI summary";
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

            renderAiSummary({
                ...baseData,
                ai_status: ai.status || "failed",
                ai_summary: ai.summary || "",
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
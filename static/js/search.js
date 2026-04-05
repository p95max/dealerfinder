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
function renderAiSummaryLoading() {
    const container = document.getElementById("modalAiSummary");
    if (!container) return;

    container.classList.remove("d-none");

    container.innerHTML = `
        <div class="alert alert-secondary mt-3 mb-0 small">
            <div class="d-flex align-items-center gap-2 mb-1">
                <div class="spinner-border spinner-border-sm"></div>
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

    const interval = setInterval(() => {
        if (i < steps.length) {
            textEl.textContent = steps[i];
            i++;
        } else {
            clearInterval(interval);
        }
    }, 800);
}

function openDealerModal(btn) {
    const modalEl = document.getElementById("dealerModal");
    const nameEl = document.getElementById("modalDealerName");
    const infoEl = document.getElementById("modalInfo");
    const mapEl = document.getElementById("modalMap");
    const routeBtn = document.getElementById("modalRouteBtn");

    const data = {
        name: btn.dataset.dealerName || "",
        address: btn.dataset.dealerAddress || "",
        phone: btn.dataset.dealerPhone || "",
        website: btn.dataset.dealerWebsite || "",
        rating: btn.dataset.dealerRating || "",
        distance: btn.dataset.dealerDistance || "",
        lat: btn.dataset.dealerLat,
        lng: btn.dataset.dealerLng,
        ai_summary: btn.dataset.dealerAiSummary || "",
        ai_status: btn.dataset.dealerAiStatus || "pending",
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
    }

    const placeId = btn.dataset.dealerPlaceId;

    if (data.ai_status === "done") {
        renderAiSummary(data);
    } else {
        renderAiSummaryLoading();
        fetch(`/dealer/${placeId}/ai-summary/`)
            .then(r => r.json())
            .then(ai => {
                btn.dataset.dealerAiStatus = ai.status;
                btn.dataset.dealerAiSummary = ai.summary;
                renderAiSummary({ ...data, ai_status: ai.status, ai_summary: ai.summary });
            })
            .catch(() => renderAiSummary({ ...data, ai_status: "failed" }));
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
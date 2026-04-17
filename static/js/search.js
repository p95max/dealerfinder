document.addEventListener("DOMContentLoaded", () => {
    initLocationFeatures();
    initCityAutocomplete();
    initLiveSearchPanel();
});


/* =========================
   GEOLOCATION FEATURES
========================= */
function initLocationFeatures() {
    const form = document.getElementById("dealerSearchForm");
    const detectButton = document.getElementById("detectLocationBtn");
    const cityInput = document.getElementById("city");
    const sortInput = document.getElementById("sort");
    const locationHelp = document.getElementById("locationHelp");

    const searchLatInput = document.getElementById("search_lat");
    const searchLngInput = document.getElementById("search_lng");

    const originLatInput = document.getElementById("origin_lat");
    const originLngInput = document.getElementById("origin_lng");
    const showDistanceCheckbox = document.getElementById("show_distance_from_me");

    if (!form) return;
    if (form.dataset.geoInitialized === "1") return;
    form.dataset.geoInitialized = "1";

    const GEO_CACHE_KEY = "dealerfinder_user_geolocation";

    function setMessage(message, isError = false) {
        if (!locationHelp) return;
        locationHelp.textContent = message;
        locationHelp.classList.toggle("text-danger", isError);
    }

    function setButtonLoading(isLoading, loadingText = "Detecting...") {
        if (!detectButton) return;

        detectButton.disabled = isLoading;

        if (isLoading) {
            if (!detectButton.dataset.originalText) {
                detectButton.dataset.originalText = detectButton.textContent.trim();
            }
            detectButton.textContent = loadingText;
        } else if (detectButton.dataset.originalText) {
            detectButton.textContent = detectButton.dataset.originalText;
        }
    }

    function readCachedPosition() {
        try {
            const raw = sessionStorage.getItem(GEO_CACHE_KEY);
            if (!raw) return null;

            const data = JSON.parse(raw);
            if (
                !data ||
                !isFiniteCoordinate(data.lat, -90, 90) ||
                !isFiniteCoordinate(data.lng, -180, 180)
            ) {
                return null;
            }

            return data;
        } catch {
            return null;
        }
    }

    function cachePosition(lat, lng) {
        try {
            sessionStorage.setItem(
                GEO_CACHE_KEY,
                JSON.stringify({
                    lat,
                    lng,
                    savedAt: Date.now(),
                })
            );
        } catch {
            // ignore storage failures
        }
    }

    function requestBrowserPosition({ onSuccess, onError }) {
        if (!navigator.geolocation) {
            onError({
                code: -1,
                message: "Geolocation is not supported by your browser.",
            });
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                cachePosition(lat, lng);
                onSuccess({ lat, lng });
            },
            (error) => {
                if (error.code === 3) {
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            const lat = position.coords.latitude;
                            const lng = position.coords.longitude;

                            cachePosition(lat, lng);
                            onSuccess({ lat, lng });
                        },
                        onError,
                        {
                            enableHighAccuracy: false,
                            timeout: 25000,
                            maximumAge: 0,
                        }
                    );
                    return;
                }

                onError(error);
            },
            {
                enableHighAccuracy: false,
                timeout: 7000,
                maximumAge: 600000,
            }
        );
    }

    function fillGeoSearchCoords(lat, lng) {
        if (searchLatInput) searchLatInput.value = String(lat);
        if (searchLngInput) searchLngInput.value = String(lng);
    }

    function clearGeoSearchCoords() {
        if (searchLatInput) searchLatInput.value = "";
        if (searchLngInput) searchLngInput.value = "";
    }

    function fillOriginCoords(lat, lng) {
        if (originLatInput) originLatInput.value = String(lat);
        if (originLngInput) originLngInput.value = String(lng);
    }

    function clearOriginCoords() {
        if (originLatInput) originLatInput.value = "";
        if (originLngInput) originLngInput.value = "";
    }

    function handleGeoError(error) {
        console.warn("Geolocation error:", {
            code: error.code,
            message: error.message,
        });

        let msg = "Unable to detect your location.";
        if (error.code === 1) msg = "Permission denied.";
        if (error.code === 2) msg = "Position unavailable.";
        if (error.code === 3) msg = "Request timed out. Try again.";
        if (error.code === -1) msg = error.message;

        setButtonLoading(false);
        setMessage(msg, true);
    }

    function handleUseMyLocationClick() {
        setButtonLoading(true);
        setMessage("Detecting your location...");

        requestBrowserPosition({
            onSuccess: ({ lat, lng }) => {
                fillGeoSearchCoords(lat, lng);

                // For geo search scenario we intentionally clear manual city
                if (cityInput) {
                    cityInput.value = "";
                }

                // Distance sorting makes sense for "near me"
                if (sortInput) {
                    sortInput.value = "distance";
                }

                setButtonLoading(false);
                setMessage("Location detected. Searching near you...");
                form.requestSubmit();
            },
            onError: handleGeoError,
        });
    }

    async function ensureOriginCoordsBeforeSubmit(event) {
        if (!showDistanceCheckbox || !showDistanceCheckbox.checked) {
            clearOriginCoords();
            return;
        }

        const cached = readCachedPosition();
        if (cached) {
            fillOriginCoords(cached.lat, cached.lng);
            setMessage("Your location will be used to show dealer distance.");
            return;
        }

        event.preventDefault();
        setMessage("Detecting your location for distance calculation...");

        requestBrowserPosition({
            onSuccess: ({ lat, lng }) => {
                fillOriginCoords(lat, lng);
                setMessage("Location detected. Distance from you is enabled.");
                form.requestSubmit();
            },
            onError: (error) => {
                clearOriginCoords();
                handleGeoError(error);
            },
        });
    }

    if (detectButton) {
        detectButton.addEventListener("click", handleUseMyLocationClick);
    }

    form.addEventListener("submit", ensureOriginCoordsBeforeSubmit);

    if (showDistanceCheckbox) {
        showDistanceCheckbox.addEventListener("change", () => {
            if (!showDistanceCheckbox.checked) {
                clearOriginCoords();
                setMessage("");
                return;
            }

            const cached = readCachedPosition();
            if (cached) {
                fillOriginCoords(cached.lat, cached.lng);
                setMessage("Distance from you is enabled.");
            }
        });
    }
}


/* =========================
   AUTOCOMPLETE (CITY)
========================= */
function initCityAutocomplete() {
    fetch("/static/data/cities_de.json")
        .then((r) => r.json())
        .then((cities) => {
            const input = document.getElementById("city");
            const datalist = document.getElementById("cities-list");
            if (!input || !datalist) return;

            input.addEventListener("input", () => {
                const val = input.value.toLowerCase().trim();
                datalist.innerHTML = "";

                if (val.length < 2) return;

                cities
                    .filter((c) => c.toLowerCase().startsWith(val))
                    .slice(0, 10)
                    .forEach((c) => {
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

function escapeHtml(str) {
    return String(str)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

/* =========================
   UX
========================= */

document.addEventListener("DOMContentLoaded", function () {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (el) {
        new bootstrap.Tooltip(el);
    });
});

function initLiveSearchPanel() {
    const form = document.getElementById("dealerSearchForm");
    if (!form) return;

    const cityInput = document.getElementById("city");
    const radiusInput = document.getElementById("radius");
    const sortInput = document.getElementById("sort");
    const minRatingInput = document.getElementById("min_rating");
    const maxDistanceInput = document.getElementById("max_distance_km");
    const openNowInput = document.getElementById("open_now");
    const weekendsInput = document.getElementById("weekends");
    const hasContactsInput = document.getElementById("has_contacts");
    const showDistanceInput = document.getElementById("show_distance_from_me");

    const liveFields = [
        radiusInput,
        sortInput,
        minRatingInput,
        maxDistanceInput,
        openNowInput,
        weekendsInput,
        hasContactsInput,
        showDistanceInput,
    ].filter(Boolean);

    let debounceTimer = null;

    function hasSearchContext() {
        return Boolean(
            (cityInput && cityInput.value.trim()) ||
            (document.getElementById("search_lat")?.value && document.getElementById("search_lng")?.value)
        );
    }

    function submitLive() {
        if (!hasSearchContext()) return;

        window.clearTimeout(debounceTimer);
        debounceTimer = window.setTimeout(() => {
            form.requestSubmit();
        }, 250);
    }

    liveFields.forEach((field) => {
        const eventName =
            field.type === "checkbox" || field.tagName === "SELECT"
                ? "change"
                : "input";

        field.addEventListener(eventName, submitLive);
    });
}

function initViewedDealersHighlight() {
    const STORAGE_KEY = "dealerfinder_viewed";

    function getViewed() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    }

    function saveViewed(list) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, 50)));
        } catch {
            // ignore storage failures
        }
    }

    function markViewed(placeId) {
        if (!placeId) return;

        const viewed = [placeId, ...getViewed().filter((id) => id !== placeId)];
        saveViewed(viewed);
    }

    function applyViewedState(card) {
        if (!card) return;
        card.classList.add("dealer-viewed");
    }

    function applyHighlightFromStorage() {
        const viewed = new Set(getViewed());

        document.querySelectorAll(".dealer-card").forEach((card) => {
            const placeId = card.dataset.dealerPlaceId || "";
            if (viewed.has(placeId)) {
                applyViewedState(card);
            }
        });
    }

    document.querySelectorAll(".dealer-card").forEach((card) => {
        card.addEventListener("click", () => {
            const placeId = card.dataset.dealerPlaceId || "";
            if (!placeId) return;

            markViewed(placeId);
            applyViewedState(card);
        });
    });

    applyHighlightFromStorage();
}

document.addEventListener("DOMContentLoaded", initViewedDealersHighlight);
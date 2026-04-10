document.addEventListener("DOMContentLoaded", () => {
    initLocationButton();
    initCityAutocomplete();
});


/* =========================
   GEOLOCATION (BUTTON)
========================= */
function initLocationButton() {
    const form = document.getElementById("dealerSearchForm");
    const button = document.getElementById("detectLocationBtn");
    const latInput = document.getElementById("user_lat");
    const lngInput = document.getElementById("user_lng");
    const cityInput = document.getElementById("city");
    const sortInput = document.getElementById("sort");
    const locationHelp = document.getElementById("locationHelp");

    if (!form || !button || !latInput || !lngInput) return;

    if (button.dataset.geoInitialized === "1") return;
    button.dataset.geoInitialized = "1";

    function setMessage(message, isError = false) {
        if (!locationHelp) return;
        locationHelp.textContent = message;
        locationHelp.classList.toggle("text-danger", isError);
    }

    function setLoading(isLoading, loadingText = "Detecting...") {
        button.disabled = isLoading;

        if (isLoading) {
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.textContent.trim();
            }
            button.textContent = loadingText;
        } else if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
        }
    }

    function submitWithLocation(position) {
        latInput.value = String(position.coords.latitude);
        lngInput.value = String(position.coords.longitude);

        // Important: clear city so backend can resolve it from coordinates
        if (cityInput) {
            cityInput.value = "";
        }

        // Optional but useful: show nearby results first
        if (sortInput) {
            sortInput.value = "distance";
        }

        setLoading(false);
        setMessage("Location detected. Searching near you...");

        form.requestSubmit();
    }

    function handleError(error) {
        console.warn("Geolocation error:", {
            code: error.code,
            message: error.message,
        });

        let msg = "Unable to detect your location.";

        if (error.code === 1) msg = "Permission denied.";
        if (error.code === 2) msg = "Position unavailable.";
        if (error.code === 3) msg = "Request timed out. Try again.";

        setLoading(false);
        setMessage(msg, true);
    }

    function requestPosition() {
        navigator.geolocation.getCurrentPosition(
            submitWithLocation,
            (error) => {
                if (error.code === 3) {
                    navigator.geolocation.getCurrentPosition(
                        submitWithLocation,
                        handleError,
                        {
                            enableHighAccuracy: false,
                            timeout: 25000,
                            maximumAge: 0,
                        }
                    );
                    return;
                }

                handleError(error);
            },
            {
                enableHighAccuracy: false,
                timeout: 7000,
                maximumAge: 600000,
            }
        );
    }

    button.addEventListener("click", () => {
        if (!navigator.geolocation) {
            setMessage("Geolocation is not supported by your browser.", true);
            return;
        }

        setLoading(true);
        setMessage("Detecting your location...");

        requestPosition();
    });
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
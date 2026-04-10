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

    button.addEventListener("click", () => {
        if (!navigator.geolocation) {
            setMessage("Geolocation is not supported by your browser.", true);
            return;
        }

        setLoading(true);
        setMessage("Detecting your location...");

        navigator.geolocation.getCurrentPosition(
            (position) => {
                latInput.value = String(position.coords.latitude);
                lngInput.value = String(position.coords.longitude);

                setLoading(false);
                setMessage("Location detected. Now click Search dealers.");
            },
            (error) => {
                let msg = "Unable to detect your location.";

                if (error.code === 1) msg = "Permission denied.";
                if (error.code === 2) msg = "Position unavailable.";
                if (error.code === 3) msg = "Request timed out.";

                setLoading(false);
                setMessage(msg, true);
            },
            {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 300000,
            }
        );
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
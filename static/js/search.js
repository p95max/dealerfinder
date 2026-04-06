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
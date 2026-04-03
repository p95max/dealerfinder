document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("dealerSearchForm");
    const locationCheckbox = document.getElementById("use_my_location");
    const latInput = document.getElementById("user_lat");
    const lngInput = document.getElementById("user_lng");
    const searchButton = form ? form.querySelector('button[type="submit"]') : null;
    const locationHelp = document.getElementById("locationHelp");

    if (!form || !locationCheckbox || !latInput || !lngInput || !searchButton) {
        return;
    }

    let geoRequestInProgress = false;

    function setLocationMessage(message, isError = false) {
        if (!locationHelp) {
            return;
        }

        locationHelp.textContent = message;
        locationHelp.classList.toggle("text-danger", isError);
    }

    function clearCoordinates() {
        latInput.value = "";
        lngInput.value = "";
    }

    function hasCoordinates() {
        return latInput.value.trim() !== "" && lngInput.value.trim() !== "";
    }

    function setLoadingState(isLoading) {
        geoRequestInProgress = isLoading;
        searchButton.disabled = isLoading;

        if (isLoading) {
            searchButton.dataset.originalText = searchButton.textContent;
            searchButton.textContent = "Detecting location...";
        } else if (searchButton.dataset.originalText) {
            searchButton.textContent = searchButton.dataset.originalText;
        }
    }

    function requestUserLocation(onSuccess = null) {
        if (!navigator.geolocation) {
            setLocationMessage("Geolocation is not supported in this browser.", true);
            locationCheckbox.checked = false;
            clearCoordinates();
            return;
        }

        setLoadingState(true);
        setLocationMessage("Detecting your location...");

        navigator.geolocation.getCurrentPosition(
            (position) => {
                latInput.value = String(position.coords.latitude);
                lngInput.value = String(position.coords.longitude);

                setLoadingState(false);
                setLocationMessage("Location detected successfully.");

                if (typeof onSuccess === "function") {
                    onSuccess();
                }
            },
            (error) => {
                clearCoordinates();
                locationCheckbox.checked = false;
                setLoadingState(false);

                let message = "Could not access your location.";
                if (error.code === error.PERMISSION_DENIED) {
                    message = "Location access was denied.";
                } else if (error.code === error.TIMEOUT) {
                    message = "Location request timed out.";
                }

                setLocationMessage(message, true);
            },
            {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 300000,
            }
        );
    }

    locationCheckbox.addEventListener("change", () => {
        if (!locationCheckbox.checked) {
            clearCoordinates();
            setLocationMessage(
                "Location is optional. If enabled, we will use your coordinates only for distance-based filtering and sorting."
            );
            return;
        }

        requestUserLocation();
    });

    form.addEventListener("submit", (event) => {
        if (!locationCheckbox.checked) {
            return;
        }

        if (geoRequestInProgress) {
            event.preventDefault();
            return;
        }

        if (hasCoordinates()) {
            return;
        }

        event.preventDefault();
        requestUserLocation(() => {
            form.submit();
        });
    });
});


fetch("/static/data/cities_de.json")
    .then(r => r.json())
    .then(cities => {
        const input = document.getElementById("city");
        const datalist = document.getElementById("cities-list");
        if (!input || !datalist) return;

        input.addEventListener("input", () => {
            const val = input.value.trim().toLowerCase();
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
    });


function isFiniteCoordinate(value, min, max) {
    const num = Number(value);
    return Number.isFinite(num) && num >= min && num <= max;
}

function toSafeExternalUrl(value) {
    if (!value) {
        return null;
    }

    try {
        const url = new URL(value);
        if (url.protocol !== "http:" && url.protocol !== "https:") {
            return null;
        }
        return url.href;
    } catch {
        return null;
    }
}

function appendInfoRow(container, label, value, options = {}) {
    if (!value) {
        return;
    }

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

function openDealerModal(btn) {
    const modalEl = document.getElementById("dealerModal");
    const nameEl = document.getElementById("modalDealerName");
    const infoEl = document.getElementById("modalInfo");
    const mapEl = document.getElementById("modalMap");
    const routeBtn = document.getElementById("modalRouteBtn");

    if (!modalEl || !nameEl || !infoEl || !mapEl || !routeBtn) {
        return;
    }

    const d = {
        place_id: btn.dataset.dealerPlaceId || "",
        name: btn.dataset.dealerName || "",
        address: btn.dataset.dealerAddress || "",
        phone: btn.dataset.dealerPhone || "",
        website: btn.dataset.dealerWebsite || "",
        rating: btn.dataset.dealerRating || "",
        reviews: btn.dataset.dealerReviews || "",
        lat: btn.dataset.dealerLat || "",
        lng: btn.dataset.dealerLng || "",
        distance: btn.dataset.dealerDistance || "",
        city: btn.dataset.dealerCity || "",
        is_favorite: btn.dataset.dealerIsFavorite === "1",
    };

    nameEl.textContent = d.name;
    infoEl.replaceChildren();

    appendInfoRow(infoEl, "Address", d.address);
    appendInfoRow(infoEl, "Phone", d.phone);

    const safeWebsite = toSafeExternalUrl(d.website);
    if (safeWebsite) {
        appendInfoRow(infoEl, "Website", safeWebsite, { href: safeWebsite });
    }

    appendInfoRow(infoEl, "Rating", d.rating);
    appendInfoRow(infoEl, "Distance", d.distance ? `${d.distance} km` : "");

    const hasValidCoords =
        isFiniteCoordinate(d.lat, -90, 90) &&
        isFiniteCoordinate(d.lng, -180, 180);

    if (hasValidCoords) {
        const lat = Number(d.lat);
        const lng = Number(d.lng);

        mapEl.src = `https://maps.google.com/maps?q=${lat},${lng}&z=15&output=embed`;
        routeBtn.href = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
        routeBtn.classList.remove("disabled");
        routeBtn.setAttribute("aria-disabled", "false");
    } else {
        mapEl.src = "";
        routeBtn.href = "#";
        routeBtn.classList.add("disabled");
        routeBtn.setAttribute("aria-disabled", "true");
    }

    const favBtn = document.getElementById("modalFavoriteBtn");
    if (favBtn) {
        if (d.is_favorite) {
            favBtn.classList.add("d-none");
            favBtn.disabled = true;
            favBtn.onclick = null;
        } else {
            favBtn.classList.remove("d-none");
            favBtn.disabled = false;
            favBtn.onclick = () => addFavorite(favBtn, d);
        }
    }

    bootstrap.Modal.getOrCreateInstance(modalEl).show();
}


document.addEventListener("click", (event) => {
    const btn = event.target.closest(".js-open-dealer-modal");
    if (!btn) {
        return;
    }

    openDealerModal(btn);
});
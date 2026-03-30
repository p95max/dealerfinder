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
    };

    nameEl.textContent = d.name;
    infoEl.innerHTML = "";

    if (d.address) infoEl.innerHTML += `<div><b>Address:</b> ${d.address}</div>`;
    if (d.phone) infoEl.innerHTML += `<div><b>Phone:</b> ${d.phone}</div>`;
    if (d.website) {
        infoEl.innerHTML += `<div><b>Website:</b> <a href="${d.website}" target="_blank" rel="noopener noreferrer">${d.website}</a></div>`;
    }
    if (d.rating) infoEl.innerHTML += `<div><b>Rating:</b> ${d.rating}</div>`;
    if (d.distance) infoEl.innerHTML += `<div><b>Distance:</b> ${d.distance} km</div>`;

    if (d.lat && d.lng) {
        mapEl.src = `https://maps.google.com/maps?q=${d.lat},${d.lng}&z=15&output=embed`;
        routeBtn.href = `https://www.google.com/maps/dir/?api=1&destination=${d.lat},${d.lng}`;
        routeBtn.classList.remove("disabled");
    } else {
        mapEl.src = "";
        routeBtn.href = "#";
        routeBtn.classList.add("disabled");
    }

    const favBtn = document.getElementById("modalFavoriteBtn");
    if (favBtn && typeof addFavorite === "function") {
        favBtn.onclick = () => addFavorite(favBtn, d);
        favBtn.textContent = "♡ Save";
        favBtn.disabled = false;
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
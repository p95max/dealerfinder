function addFavorite(btn, d) {
    const fd = new FormData();
    fd.append("place_id", d.place_id);
    fd.append("name", d.name);
    fd.append("address", d.address || "");
    fd.append("city", d.city || "");
    fd.append("rating", d.rating || "");
    fd.append("phone", d.phone || "");
    fd.append("website", d.website || "");
    fd.append("lat", d.lat || "");
    fd.append("lng", d.lng || "");

    fetch(window.FAVORITE_ADD_URL, {
        method: "POST",
        headers: {"X-CSRFToken": window.CSRF_TOKEN},
        body: fd,
    }).then(r => {
        if (r.ok) {
            markDealerAsFavorite(d.place_id);

            if (btn) {
                btn.classList.add("d-none");
                btn.disabled = true;
            }
        }
    });
}

function markDealerAsFavorite(placeId) {
    document.querySelectorAll(`[data-dealer-place-id="${placeId}"]`).forEach((el) => {
        el.dataset.dealerIsFavorite = "1";
        ensureFavoriteBadge(el);
    });
}

function ensureFavoriteBadge(cardEl) {
    const badgesRow = cardEl.querySelector(".dealer-badges");
    if (!badgesRow) {
        return;
    }

    const existing = badgesRow.querySelector(".js-favorite-badge");
    if (existing) {
        return;
    }

    const badge = document.createElement("span");
    badge.className = "status-badge js-favorite-badge";
    badge.textContent = "⭐ In favorites";
    badgesRow.appendChild(badge);
}

function getCookie(name) {
    return document.cookie.split(";")
        .find(c => c.trim().startsWith(name + "="))
        ?.split("=")[1];
}
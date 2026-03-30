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
            btn.textContent = "★ Saved";
            btn.disabled = true;
        }
    });
}

function getCookie(name) {
    return document.cookie.split(";")
        .find(c => c.trim().startsWith(name + "="))
        ?.split("=")[1];
}
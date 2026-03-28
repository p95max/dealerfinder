document.addEventListener("DOMContentLoaded", () => {
    const quotaCounter = document.getElementById("quota-counter");
    if (!quotaCounter) {
        return;
    }

    const quotaUrl = quotaCounter.dataset-url;
    if (!quotaUrl) {
        return;
    }

    function refreshQuota() {
        fetch(quotaUrl)
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to load quota");
                }
                return response.json();
            })
            .then((data) => {
                quotaCounter.textContent = `${data.used} / ${data.limit}`;
            })
            .catch(() => {
                // silent fail
            });
    }

    refreshQuota();

    const searchForm = document.getElementById("dealerSearchForm");
    if (searchForm) {
        searchForm.addEventListener("submit", () => {
            setTimeout(refreshQuota, 500);
        });
    }
});
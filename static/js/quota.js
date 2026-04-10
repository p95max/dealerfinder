async function refreshQuotaCounters() {
    try {
        const response = await fetch("/users/quota-status/", {
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            credentials: "same-origin",
        });

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        document.querySelectorAll("[data-quota-search-text]").forEach((el) => {
            el.textContent = `${data.search_used} / ${data.search_limit}`;
        });

        document.querySelectorAll("[data-quota-ai-text]").forEach((el) => {
            el.textContent = `${data.ai_used} / ${data.ai_limit}`;
        });

        document.querySelectorAll("[data-quota-search-bar]").forEach((el) => {
            const percent = data.search_limit
                ? Math.min((data.search_used / data.search_limit) * 100, 100)
                : 0;

            el.style.width = `${percent}%`;
            el.classList.toggle("bg-danger", data.search_used >= data.search_limit);
        });

        document.querySelectorAll("[data-quota-ai-bar]").forEach((el) => {
            const percent = data.ai_limit
                ? Math.min((data.ai_used / data.ai_limit) * 100, 100)
                : 0;

            el.style.width = `${percent}%`;
            el.classList.toggle("bg-danger", data.ai_used >= data.ai_limit);
        });
    } catch (_error) {
        // silent fail
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const hasQuotaUi =
        document.querySelector("[data-quota-search-text]") ||
        document.querySelector("[data-quota-ai-text]") ||
        document.querySelector("[data-quota-search-bar]") ||
        document.querySelector("[data-quota-ai-bar]");

    if (!hasQuotaUi) {
        return;
    }

    refreshQuotaCounters();
    setInterval(refreshQuotaCounters, 30000);
});
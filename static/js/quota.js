document.addEventListener("DOMContentLoaded", () => {
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

            const searchText = document.querySelector("[data-quota-search-text]");
            const aiText = document.querySelector("[data-quota-ai-text]");
            const searchBar = document.querySelector("[data-quota-search-bar]");
            const aiBar = document.querySelector("[data-quota-ai-bar]");

            if (searchText) {
                searchText.textContent = `${data.search_used} / ${data.search_limit}`;
            }

            if (aiText) {
                aiText.textContent = `${data.ai_used} / ${data.ai_limit}`;
            }

            if (searchBar) {
                const percent = data.search_limit
                    ? Math.min((data.search_used / data.search_limit) * 100, 100)
                    : 0;

                searchBar.style.width = `${percent}%`;
                searchBar.classList.toggle("bg-danger", data.search_used >= data.search_limit);
            }

            if (aiBar) {
                const percent = data.ai_limit
                    ? Math.min((data.ai_used / data.ai_limit) * 100, 100)
                    : 0;

                aiBar.style.width = `${percent}%`;
                aiBar.classList.toggle("bg-danger", data.ai_used >= data.ai_limit);
            }
        } catch (_error) {
            // silent fail
        }
    }

    refreshQuotaCounters();
    setInterval(refreshQuotaCounters, 30000);
});
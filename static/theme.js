// ── Light / dark theme ───────────────────────────────────────────────────────
// Loaded in every page's <head> (not deferred) so the saved theme is applied
// before the page is drawn — otherwise dark-mode users see a white flash.
// The theme is stored per browser in localStorage; light is the default.

(function () {
    const STORAGE_KEY = "theme";

    function getSavedTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
        } catch (e) {
            return "light";  // storage blocked (e.g. some private windows)
        }
    }

    function applyTheme(theme) {
        document.documentElement.dataset.theme = theme;
        document.querySelectorAll(".theme-toggle").forEach(btn => {
            const label = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
            btn.setAttribute("aria-label", label);
            btn.setAttribute("title", label);
        });
    }

    function toggleTheme() {
        const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch (e) {
            // Still switch for this page view even if it can't be saved
        }
        applyTheme(next);
    }

    applyTheme(getSavedTheme());

    // One listener for every toggle button, including ones added later by
    // script.js when it builds the navbar.
    document.addEventListener("click", (e) => {
        if (e.target.closest(".theme-toggle")) toggleTheme();
    });

    // Refresh button labels once the page's own buttons exist
    document.addEventListener("DOMContentLoaded", () => applyTheme(document.documentElement.dataset.theme));

    // Keep other open tabs in sync when the theme is changed in one of them
    window.addEventListener("storage", (e) => {
        if (e.key === STORAGE_KEY) applyTheme(getSavedTheme());
    });

    window.refreshThemeToggles = () => applyTheme(document.documentElement.dataset.theme);
})();

const loadingEl      = document.querySelector("#loading");
const containerEl    = document.querySelector("#items-container");
const searchInput    = document.querySelector("#search");
const categorySelect = document.querySelector("#category-filter");

let currentUserId = null;

// ── "Seen" tracking for the current user's own items ────────────────────────
// An item stays highlighted until the user clicks into it once; the "You"
// tag itself is derived from posted_by and never goes away.
function getSeenOwnItems() {
    try {
        return JSON.parse(localStorage.getItem("seenOwnItems") || "[]");
    } catch (e) {
        return [];
    }
}

function markOwnItemSeen(id) {
    const seen = getSeenOwnItems();
    if (!seen.includes(id)) {
        seen.push(id);
        localStorage.setItem("seenOwnItems", JSON.stringify(seen));
    }
}

// ── Navbar ─────────────────────────────────────────────────────────────────
async function initNavbar() {
    const actionsEl = document.getElementById("navbar-actions");
    if (!actionsEl) return;

    try {
        const res  = await fetch("/api/me");
        const data = await res.json();

        if (data.logged_in) {
            currentUserId = data.user_id;
            // Get initials for avatar placeholder
            const initials = data.full_name
                .split(" ")
                .map(n => n[0])
                .join("")
                .toUpperCase()
                .slice(0, 2);

            actionsEl.innerHTML = `
                <a href="/post-item" class="btn-post">+ Post Item</a>
                <div class="nav-user" id="nav-user">
                    <button class="avatar-btn" id="avatar-btn" aria-label="User menu">
                        <div class="avatar">${initials}</div>
                        <span class="nav-name">${data.full_name}</span>
                        <svg class="chevron" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                        </svg>
                    </button>
                    <div class="dropdown" id="dropdown">
                        <div class="dropdown-header">
                            <p class="dropdown-name">${data.full_name}</p>
                            <p class="dropdown-email">${data.email}</p>
                        </div>
                        <hr class="dropdown-divider">
                        <button class="dropdown-item signout-btn" id="signout-btn">
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1"/>
                            </svg>
                            Sign out
                        </button>
                    </div>
                </div>
            `;

            // Toggle dropdown
            const avatarBtn  = document.getElementById("avatar-btn");
            const dropdown   = document.getElementById("dropdown");
            const backdrop   = document.getElementById("dropdown-backdrop");

            avatarBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const open = dropdown.classList.toggle("open");
                backdrop.classList.toggle("hidden", !open);
            });

            backdrop.addEventListener("click", () => {
                dropdown.classList.remove("open");
                backdrop.classList.add("hidden");
            });

            // Sign out
            document.getElementById("signout-btn").addEventListener("click", async () => {
                try {
                    const res = await fetch("/api/logout", { method: "POST" });
                    if (res.ok) {
                        window.location.href = "/";
                    } else {
                        alert("Sign out failed. Please try again.");
                    }
                } catch (e) {
                    alert("Sign out failed. Please try again.");
                }
            });

        } else {
            actionsEl.innerHTML = `
                <a href="/register" class="btn-outline">Sign Up</a>
                <a href="/login"    class="btn-primary">Log In</a>
            `;
        }
    } catch (e) {
        console.error("Navbar init failed:", e);
    }
}

// ── Items ───────────────────────────────────────────────────────────────────
function renderItems(items) {
    if (!containerEl) return;
    containerEl.innerHTML = "";

    if (items.length === 0) {
        containerEl.innerHTML = "<p>No items match your search.</p>";
        return;
    }

    const seenOwnItems = getSeenOwnItems();

    items.forEach(item => {
        const card = document.createElement("a");
        card.href  = `/items/${item.id}`;
        card.classList.add("item-card");
        card.dataset.category = item.category;

        const isMine = currentUserId !== null && item.posted_by === currentUserId;
        if (isMine) {
            if (!seenOwnItems.includes(item.id)) {
                card.classList.add("item-card--new");
            }
            card.addEventListener("click", () => markOwnItemSeen(item.id));
        }

        const title = document.createElement("h3");
        title.textContent = item.title;

        const badge = document.createElement("span");
        badge.classList.add("badge");
        badge.textContent = item.category;

        const poster = document.createElement("p");
        poster.classList.add("card-poster");
        poster.textContent = item.posted_by_name ? `By ${item.posted_by_name}` : "";

        card.appendChild(title);
        card.appendChild(badge);
        if (isMine) {
            const youBadge = document.createElement("span");
            youBadge.classList.add("badge-you");
            youBadge.textContent = "You";
            card.appendChild(youBadge);
        }
        if (item.posted_by_name) card.appendChild(poster);
        containerEl.appendChild(card);
    });
}

async function loadItems() {
    if (!containerEl) return;
    const params   = new URLSearchParams();
    const search   = searchInput ? searchInput.value.trim() : "";
    const category = categorySelect ? categorySelect.value : "";
    if (search)   params.set("search",   search);
    if (category) params.set("category", category);

    if (loadingEl) loadingEl.style.display = "block";
    try {
        const response = await fetch("/api/items?" + params.toString());
        const items    = await response.json();
        renderItems(items);
    } catch (error) {
        containerEl.innerHTML = "<p>Something went wrong loading items.</p>";
    } finally {
        if (loadingEl) loadingEl.style.display = "none";
    }
}

let debounceTimer;
function debouncedLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadItems, 300);
}

if (searchInput)    searchInput.addEventListener("input", debouncedLoad);
if (categorySelect) categorySelect.addEventListener("change", loadItems);

// ── Init ────────────────────────────────────────────────────────────────────
(async () => {
    await initNavbar();
    if (containerEl) loadItems();
})();
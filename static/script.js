const loadingEl      = document.querySelector("#loading");
const containerEl    = document.querySelector("#items-container");
const searchInput    = document.querySelector("#search");
const categorySelect = document.querySelector("#category-filter");

let currentUserId = null;
let currentNotifIds = [];

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

// ── "Seen" tracking for notifications ────────────────────────────────────────
// Each notification has an id derived from its underlying claim request and
// status (e.g. "outgoing-5-confirmed"), so a request that changes status
// reads as a new, unseen notification even though its request id repeats.
function getSeenNotifIds() {
    try {
        return JSON.parse(localStorage.getItem("seenNotifIds") || "[]");
    } catch (e) {
        return [];
    }
}

function markNotifsSeen(ids) {
    const seen = getSeenNotifIds();
    ids.forEach(id => {
        if (!seen.includes(id)) seen.push(id);
    });
    localStorage.setItem("seenNotifIds", JSON.stringify(seen.slice(-300)));
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : str;
    return div.innerHTML;
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
                <div class="nav-notif" id="nav-notif">
                    <button class="bell-btn" id="bell-btn" aria-label="Notifications">
                        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                        </svg>
                        <span class="notif-badge hidden" id="notif-badge">0</span>
                    </button>
                    <div class="dropdown notif-dropdown" id="notif-dropdown">
                        <div class="dropdown-header">
                            <p class="dropdown-name">Notifications</p>
                        </div>
                        <hr class="dropdown-divider">
                        <div id="notif-list" class="notif-list">
                            <p class="notif-empty">Loading…</p>
                        </div>
                    </div>
                </div>
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
                        <a href="/users/${data.user_id}" class="dropdown-item">
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A7 7 0 0112 15a7 7 0 016.879 2.804M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                            </svg>
                            My Profile
                        </a>
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
            const avatarBtn     = document.getElementById("avatar-btn");
            const dropdown      = document.getElementById("dropdown");
            const bellBtn       = document.getElementById("bell-btn");
            const notifDropdown = document.getElementById("notif-dropdown");
            const backdrop      = document.getElementById("dropdown-backdrop");

            function closeAllDropdowns() {
                dropdown.classList.remove("open");
                notifDropdown.classList.remove("open");
                backdrop.classList.add("hidden");
            }

            avatarBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const open = !dropdown.classList.contains("open");
                closeAllDropdowns();
                if (open) {
                    dropdown.classList.add("open");
                    backdrop.classList.remove("hidden");
                }
            });

            bellBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const open = !notifDropdown.classList.contains("open");
                closeAllDropdowns();
                if (open) {
                    notifDropdown.classList.add("open");
                    backdrop.classList.remove("hidden");
                    markCurrentNotifsSeen();
                }
            });

            backdrop.addEventListener("click", closeAllDropdowns);

            // Notifications
            loadNotifications();

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

// ── Notifications ─────────────────────────────────────────────────────────────
function markCurrentNotifsSeen() {
    if (currentNotifIds.length === 0) return;
    markNotifsSeen(currentNotifIds);
    const badgeEl = document.getElementById("notif-badge");
    if (badgeEl) badgeEl.classList.add("hidden");
    document.querySelectorAll(".notif-item--unseen").forEach(el => el.classList.remove("notif-item--unseen"));
}

function outgoingNotifText(req) {
    if (req.status === "confirmed") {
        return `Your claim on <strong>${escapeHtml(req.item_title)}</strong> was confirmed`;
    }
    if (req.status === "declined") {
        return `<strong>${escapeHtml(req.item_title)}</strong> was claimed by someone else`;
    }
    if (req.status === "cancelled") {
        return `You cancelled your request for <strong>${escapeHtml(req.item_title)}</strong>`;
    }
    return `Your request for <strong>${escapeHtml(req.item_title)}</strong> is pending`;
}

function incomingNotifText(req) {
    if (req.status === "cancelled") {
        return `<strong>${escapeHtml(req.requester_name)}</strong> has cancelled the request for <strong>${escapeHtml(req.item_title)}</strong>`;
    }
    return `<strong>${escapeHtml(req.requester_name)}</strong> wants to claim <strong>${escapeHtml(req.item_title)}</strong>`;
}

function renderNotifications(data) {
    const listEl  = document.getElementById("notif-list");
    const badgeEl = document.getElementById("notif-badge");
    if (!listEl || !badgeEl) return;

    const seen = getSeenNotifIds();

    const entries = [
        ...data.incoming.map(req => ({
            sortKey: req.id,
            notifId: `incoming-${req.id}-${req.status}`,
            itemId:  req.item_id,
            body:    incomingNotifText(req)
        })),
        ...data.outgoing.map(req => ({
            sortKey: req.id,
            notifId: `outgoing-${req.id}-${req.status}`,
            itemId:  req.item_id,
            body:    outgoingNotifText(req)
        }))
    ].sort((a, b) => b.sortKey - a.sortKey);

    currentNotifIds = entries.map(e => e.notifId);

    const unseenCount = entries.filter(e => !seen.includes(e.notifId)).length;
    badgeEl.textContent = unseenCount > 9 ? "9+" : String(unseenCount);
    badgeEl.classList.toggle("hidden", unseenCount === 0);

    if (entries.length === 0) {
        listEl.innerHTML = `<p class="notif-empty">No notifications yet.</p>`;
        return;
    }

    listEl.innerHTML = entries.map(e => `
        <a href="/items/${e.itemId}" class="notif-item${seen.includes(e.notifId) ? "" : " notif-item--unseen"}">
            ${e.body}
        </a>
    `).join("");
}

async function loadNotifications() {
    try {
        const res  = await fetch("/api/notifications");
        const data = await res.json();
        renderNotifications(data);
    } catch (e) {
        console.error("Loading notifications failed:", e);
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
        if (item.status === "claimed") card.classList.add("item-card--claimed");
        if (item.status === "pending") card.classList.add("item-card--pending");

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
        if (item.status === "claimed") {
            const claimedBadge = document.createElement("span");
            claimedBadge.classList.add("badge-status", "claimed");
            claimedBadge.textContent = "Claimed";
            card.appendChild(claimedBadge);
        } else if (item.status === "pending") {
            const claimPendingBadge = document.createElement("span");
            claimPendingBadge.classList.add("badge-status", "pending");
            claimPendingBadge.textContent = "Claim pending";
            card.appendChild(claimPendingBadge);
        } else if (item.has_pending_request) {
            const requestPendingBadge = document.createElement("span");
            requestPendingBadge.classList.add("badge-status", "pending");
            requestPendingBadge.textContent = "Request pending";
            card.appendChild(requestPendingBadge);
        }
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

// ── Availability (profile page) ──────────────────────────────────────────────
function initAvailabilityEditor() {
    const form      = document.getElementById("availability-form");
    const editBtn   = document.getElementById("edit-availability-btn");
    const cancelBtn = document.getElementById("cancel-availability-btn");
    const display   = document.getElementById("availability-display");
    const input     = document.getElementById("availability-input");
    const errorEl   = document.getElementById("availability-error");
    if (!form || !editBtn) return;

    const MAX_LENGTH = 500;
    const originalValue = input.value;

    editBtn.addEventListener("click", () => {
        form.classList.remove("hidden");
        editBtn.classList.add("hidden");
        input.focus();
    });

    cancelBtn.addEventListener("click", () => {
        input.value = originalValue;
        errorEl.classList.add("hidden");
        form.classList.add("hidden");
        editBtn.classList.remove("hidden");
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const value = input.value.trim();
        if (value.length > MAX_LENGTH) {
            errorEl.classList.remove("hidden");
            return;
        }
        errorEl.classList.add("hidden");

        const userId = form.dataset.userId;
        try {
            const res = await fetch(`/api/users/${userId}/availability`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({ availability: value })
            });
            if (!res.ok) throw new Error("Request failed");
            const data = await res.json();

            if (data.availability) {
                display.textContent = data.availability;
                display.classList.remove("availability-empty");
            } else {
                display.textContent = "You haven't set your availability yet.";
                display.classList.add("availability-empty");
            }
            input.value = data.availability;

            form.classList.add("hidden");
            editBtn.classList.remove("hidden");
        } catch (err) {
            alert("Couldn't save availability. Please try again.");
        }
    });
}

// ── Claiming (item detail page) ──────────────────────────────────────────────
function initClaimActions() {
    const section = document.getElementById("claim-section");
    if (!section) return;

    const itemId = section.dataset.itemId;

    const claimBtn = section.querySelector(".claim-btn");
    if (claimBtn) {
        const errorEl = section.querySelector(".claim-error");
        const proofInput = section.querySelector(".claim-proof-input");
        claimBtn.addEventListener("click", async () => {
            const proofDetails = proofInput ? proofInput.value.trim() : "";
            if (!proofDetails) {
                if (errorEl) {
                    errorEl.textContent = "Please describe details that prove you're the true owner.";
                    errorEl.classList.remove("hidden");
                }
                if (proofInput) proofInput.focus();
                return;
            }
            if (errorEl) errorEl.classList.add("hidden");

            claimBtn.disabled = true;
            try {
                const res  = await fetch(`/api/items/${itemId}/claim`, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: new URLSearchParams({ proof_details: proofDetails })
                });
                const data = await res.json();

                if (!res.ok) {
                    if (errorEl) {
                        errorEl.textContent = data.error || "Couldn't send the claim request.";
                        errorEl.classList.remove("hidden");
                    }
                    claimBtn.disabled = false;
                    return;
                }

                window.location.reload();
            } catch (e) {
                if (errorEl) {
                    errorEl.textContent = "Couldn't send the claim request. Please try again.";
                    errorEl.classList.remove("hidden");
                }
                claimBtn.disabled = false;
            }
        });
    }

    const cancelBtn = section.querySelector(".claim-cancel-btn");
    if (cancelBtn) {
        const errorEl = section.querySelector(".claim-error");
        cancelBtn.addEventListener("click", async () => {
            if (!window.confirm("Are you sure you want to cancel the request?")) return;

            cancelBtn.disabled = true;
            try {
                const res  = await fetch(`/api/items/${itemId}/claim/cancel`, { method: "POST" });
                const data = await res.json();

                if (!res.ok) {
                    if (errorEl) {
                        errorEl.textContent = data.error || "Couldn't cancel the request.";
                        errorEl.classList.remove("hidden");
                    }
                    cancelBtn.disabled = false;
                    return;
                }

                window.location.reload();
            } catch (e) {
                if (errorEl) {
                    errorEl.textContent = "Couldn't cancel the request. Please try again.";
                    errorEl.classList.remove("hidden");
                }
                cancelBtn.disabled = false;
            }
        });
    }

    section.querySelectorAll(".claim-confirm-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const li        = btn.closest(".claim-request-item");
            const requestId = li.dataset.requestId;
            btn.disabled = true;
            li.classList.add("confirming");
            try {
                const res = await fetch(`/api/items/${itemId}/claim-requests/${requestId}/confirm`, { method: "POST" });
                if (!res.ok) throw new Error("Request failed");
                window.location.reload();
            } catch (e) {
                alert("Couldn't confirm the requester. Please try again.");
                btn.disabled = false;
                li.classList.remove("confirming");
            }
        });
    });

    const confirmClaimedBtn = section.querySelector(".confirm-claimed-btn");
    if (confirmClaimedBtn) {
        const errorEl = section.querySelector(".claim-error");
        confirmClaimedBtn.addEventListener("click", async () => {
            confirmClaimedBtn.disabled = true;
            try {
                const res  = await fetch(`/api/items/${itemId}/confirm-claimed`, { method: "POST" });
                const data = await res.json();

                if (!res.ok) {
                    if (errorEl) {
                        errorEl.textContent = data.error || "Couldn't confirm the claim.";
                        errorEl.classList.remove("hidden");
                    }
                    confirmClaimedBtn.disabled = false;
                    return;
                }

                window.location.reload();
            } catch (e) {
                if (errorEl) {
                    errorEl.textContent = "Couldn't confirm the claim. Please try again.";
                    errorEl.classList.remove("hidden");
                }
                confirmClaimedBtn.disabled = false;
            }
        });
    }
}

// ── Init ────────────────────────────────────────────────────────────────────
(async () => {
    await initNavbar();
    if (containerEl) loadItems();
    initAvailabilityEditor();
    initClaimActions();
})();
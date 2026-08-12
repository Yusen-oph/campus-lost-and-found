const loadingEl = document.querySelector("#loading");
const containerEl = document.querySelector("#items-container");
const searchInput = document.querySelector("#search");
const categorySelect = document.querySelector("#category-filter");

function renderItems(items) {
    containerEl.innerHTML = "";

    if (items.length === 0) {
        containerEl.innerHTML = "<p>No items match your search.</p>";
        return;
    }

        items.forEach(item => {
            const card = document.createElement("a");
            card.href = `/items/${item.id}`;
            card.classList.add("item-card");
            card.dataset.category = item.category;

            const title = document.createElement("h3");
            title.textContent = item.title;

            const category = document.createElement("span");
            category.classList.add("badge");
            category.textContent = item.category;

            card.appendChild(title);
            card.appendChild(category);
            containerEl.appendChild(card);
        });
}

async function loadItems() {
    const params = new URLSearchParams();
    const search = searchInput.value.trim();
    const category = categorySelect.value;
    if (search) params.set("search", search);
    if (category) params.set("category", category);

    loadingEl.style.display = "block";
    try {
        const response = await fetch("/api/items?" + params.toString());
        const items = await response.json();
        renderItems(items);
    } catch (error) {
        containerEl.innerHTML = "<p>Something went wrong loading items.</p>";
    } finally {
        loadingEl.style.display = "none";
    }
}

let debounceTimer;

function debouncedLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadItems, 300);
}

searchInput.addEventListener("input", debouncedLoad);
categorySelect.addEventListener("change", loadItems);
loadItems();
const loadingEl = document.querySelector("#loading");
const containerEl = document.querySelector("#items-container");

async function loadItems() {
    loadingEl.style.display = "block";

    try {
        const response = await fetch("/items");
        const items = await response.json();

        containerEl.innerHTML = "";
        items.forEach(item => {
            const card = document.createElement("a");
            card.href = `/items/${item.id}`;
            card.classList.add("item-card");

            const title = document.createElement("h3");
            title.textContent = item.title;

            const category = document.createElement("p");
            category.textContent = item.category;

            card.appendChild(title);
            card.appendChild(category);
            containerEl.appendChild(card);
        });
    } catch (error) {
        containerEl.innerHTML = "<p>Something went wrong loading items.</p>";
    } finally {
        loadingEl.style.display = "none";
    }
}

loadItems();
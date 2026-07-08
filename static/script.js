const loadingEl = document.querySelector("#loading");
const containerEl = document.querySelector("#items-container");

async function loadItems() {
    loadingEl.style.display = "block";

    try {
        const response = await fetch("/items");
        const items = await response.json();

        containerEl.innerHTML = "";
        items.forEach(item => {
            const card = document.createElement("div");
            card.classList.add("item-card");

            const title = document.createElement("h3");
            title.textContent = item.name;

            const location = document.createElement("p");
            location.textContent = item.location;

            card.appendChild(title);
            card.appendChild(location);
            containerEl.appendChild(card);
        });
    } catch (error) {
        containerEl.innerHTML = "<p>Something went wrong loading items.</p>";
    } finally {
        loadingEl.style.display = "none";
    }
}

loadItems();
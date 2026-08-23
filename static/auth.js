const messageEl = document.querySelector("#message");


async function submitAuth(endpoint, form) {
    const response = await fetch(endpoint, {
        method: "POST",
        body: new FormData(form),
    });
    const data = await response.json();

    if (response.ok) {
        if (endpoint === "/api/register") {
            alert("Account created successfully! Please sign in to continue.");
            window.location.href = "/login";
        } else if (endpoint === "/api/login") {
            alert("Logged in successfully! Welcome back.");
            window.location.href = "/";
        }
    } else {
        messageEl.textContent = data.error || "Something went wrong.";
    }
}


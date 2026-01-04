let challenges = [];
let currentChallengePage = 1;
const challengesPerPage = 10;

let selectedChallenges = new Set();

const buttonDownloadExample = document.getElementById("example-button");

buttonDownloadExample.addEventListener("click", () => {
        fetch(`/plugins/github_backup/challenges/download/example`, {
        method: "GET",
        credentials: "same-origin"
    })
        .then((response) => {
            if (!response.ok) throw new Error("Error during export");

            const disposition = response.headers.get("Content-Disposition");
            let filename = `challenge_example.json`;
            if (disposition && disposition.includes("filename=")) {
                filename = disposition.split("filename=")[1].replace(/"/g, "");
            }

            return response.blob().then((blob) => ({ blob, filename }));
        })
        .then(({blob, filename}) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        })
        .catch((err) => {
            alert("Unexpected Error: " + err.message);
        });

})

/**
 * Loads all challenges from the server and updates the challenge table in the DOM.
 */
function loadAllChallenges() {
    const tableBody = document.querySelector("#challenge-table tbody");
    tableBody.innerHTML = "";

    fetch("/plugins/github_backup/challenges", {
        method: "GET",
        credentials: "same-origin"
    })
        .then((response) => response.json())
        .then((data) => {
            if (!data.success) {
                throw new Error(data.message || "Could not load the challenges.");
            }

            challenges = data.challenges;

            if (challenges.length === 0) {
                const emptyRow = document.createElement("tr");
                const td = document.createElement("td");
                td.setAttribute("colspan", "4");
                td.classList.add("text-center", "text-muted");
                td.textContent = "No challenges found.";
                emptyRow.appendChild(td);
                tableBody.appendChild(emptyRow);
                return;
            }

            renderChallenges();
            renderChallengePagination();
        })
        .catch((err) => {
            alert("Unexpected Error: " + err.message);
        });
}


/**
 * Renders a table of challenges with pagination and interactive controls for exporting challenges.
 */
function renderChallenges() {
    const tableBody = document.querySelector("#challenge-table tbody");
    tableBody.innerHTML = "";

    const start = (currentChallengePage - 1) * challengesPerPage;
    const end = start + challengesPerPage;
    const pageChallenges = challenges.slice(start, end);

    pageChallenges.forEach((challenge) => {
        const tr = document.createElement("tr");

        const checkboxTd = document.createElement("td");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "export-checkbox";
        checkbox.setAttribute('data-id', challenge.id);
        checkbox.value = challenge.id;

        if (selectedChallenges.has(challenge.id)) {
            checkbox.checked = true;
        }

        checkbox.addEventListener("change", () => {
            if (checkbox.checked) {
                selectedChallenges.add(challenge.id);
            } else {
                selectedChallenges.delete(challenge.id);
            }
        });

        checkboxTd.appendChild(checkbox);

        const nameTd = document.createElement("td");
        nameTd.textContent = challenge.name;

        const importedGithubTd = document.createElement("td");
        importedGithubTd.textContent = challenge.imported ? "Yes" : "No";

        const actionsTd = document.createElement("td");
        actionsTd.innerHTML = `
            <button class="btn btn-sm btn-warning export-challenge-btn" data-id="${challenge.id}">
                <i class="fas fa-upload me-1"></i> Export
            </button>
        `;

        tr.appendChild(checkboxTd);
        tr.appendChild(nameTd);
        tr.appendChild(importedGithubTd);
        tr.appendChild(actionsTd);
        tableBody.appendChild(tr);
    });


    document.querySelectorAll(".export-challenge-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const challengeId = btn.getAttribute("data-id");
            const row = btn.closest("tr");
            const imported = row.querySelector("td:nth-child(3)").textContent === "Yes";

            let message = "Do you want to export the challenge?";
            if (!imported) {
                message += "\n\n⚠️ This challenge was not imported from GitHub.\n" +
                    "UUID fields will be generated automatically during export.";
            }

            if (confirm(message)) {
                fetch(`/plugins/github_backup/challenge/${challengeId}/download`, {
                    method: "GET",
                    credentials: "same-origin"
                })
                    .then((response) => {
                        if (!response.ok) throw new Error("Error during export");

                        const disposition = response.headers.get("Content-Disposition");
                        let filename = `challenge_${challengeId}.json`;
                        if (disposition && disposition.includes("filename=")) {
                            filename = disposition.split("filename=")[1].replace(/"/g, "");
                        }

                        return response.blob().then((blob) => ({ blob, filename }));
                    })
                    .then(({blob, filename}) => {
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                        window.URL.revokeObjectURL(url);
                    })
                    .catch((err) => {
                        alert("Unexpected Error: " + err.message);
                    });
            }
        });
    });
}

/**
 * Updates and renders the pagination controls for the challenge list.
 */
function renderChallengePagination() {
    const challengePagination = document.querySelector("#challenge-pagination");
    challengePagination.innerHTML = "";

    const totalPages = Math.ceil(challenges.length / challengesPerPage);

    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${currentChallengePage === 1 ? "disabled" : ""}`;
    prevLi.innerHTML = `<a class="page-link" href="#">Previous</a>`;
    prevLi.addEventListener("click", (e) => {
        e.preventDefault();
        if (currentChallengePage > 1) {
            currentChallengePage--;
            renderChallenges();
            renderChallengePagination();
        }
    });
    challengePagination.appendChild(prevLi);

    const pageInfo = document.createElement("li");
    pageInfo.className = "page-item disabled";
    pageInfo.innerHTML = `<span class="page-link">${currentChallengePage} / ${totalPages}</span>`;
    challengePagination.appendChild(pageInfo);

    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${currentChallengePage === totalPages ? "disabled" : ""}`;
    nextLi.innerHTML = `<a class="page-link" href="#">Next</a>`;
    nextLi.addEventListener("click", (e) => {
        e.preventDefault();
        if (currentChallengePage < totalPages) {
            currentChallengePage++;
            renderChallenges();
            renderChallengePagination();
        }
    });
    challengePagination.appendChild(nextLi);
}

loadAllChallenges();

// Export selected challenges
document.getElementById("export-selected-challenges").addEventListener("click", async () => {
    const challengeIds = Array.from(selectedChallenges);

    if (challengeIds.length === 0) {
        alert("No challenges selected");
        return;
    }

    try {
        const response = await fetch("/plugins/github_backup/challenges/download", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "CSRF-Token": CTFd.config.csrfNonce
            },
            body: JSON.stringify({ challenge_ids: challengeIds })
        });

        if (!response.ok) throw new Error("Error generating ZIP");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "challenges_export.zip";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        // Reset checkboxes
        selectedChallenges.clear();

    } catch (err) {
        console.error("Error:", err);
        alert("There was a problem exporting the challenges...");
    }
});

// Select all
document.getElementById("select-all-challenges").addEventListener("click", () => {
    challenges.forEach(ch => selectedChallenges.add(ch.id));
    renderChallenges();
});

// Unselect all
document.getElementById("deselect-all-challenges").addEventListener("click", () => {
    selectedChallenges.clear();
    renderChallenges();
});
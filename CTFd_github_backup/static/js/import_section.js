let isImportingRepos = false;

let allRepos = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 10;
let selectedRepos = new Set();

// Paginación de repos guardados
let savedRepos = [];
let savedReposPage = 1;
const SAVED_ITEMS_PER_PAGE = 4;
let selectedSavedRepos = new Set();


const githubRepoSearch = document.querySelector("#github-repo-search");
const githubReposList = document.querySelector("#github-repos-list");
const githubRepoPagination = document.querySelector("#github-repo-pagination");
const githubReposSection = document.querySelector("#github-repos-section");
const githubLoginSection = document.querySelector("#github-login-section");
const buttonSaveSelectedRepos = document.querySelector("#save-selected-repos");

githubRepoSearch?.addEventListener("input", () => {
    currentPage = 1;
    renderRepos();
});


/**
 * Renders a list of repositories based on the current search term, pagination state,
 * and the selected repositories. Filters the repositories by the search term, paginates
 * the results, and populates the repository list into the DOM.
 */
function renderRepos() {
    const searchTerm = githubRepoSearch.value.toLowerCase();
    const filteredRepos = allRepos.filter(repo =>
        repo.full_name.toLowerCase().includes(searchTerm)
    );
    const totalPages = Math.ceil(filteredRepos.length / ITEMS_PER_PAGE);
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const reposToShow = filteredRepos.slice(start, end);

    githubReposList.innerHTML = "";
    reposToShow.forEach((repo, index) => {
        const id = `repo-${start + index}`;
        const div = document.createElement("div");
        div.className = "form-check";
        div.innerHTML = `
            <input 
                class="form-check-input" 
                type="checkbox" 
                value="${repo.full_name}" 
                id="${id}"
                ${selectedRepos.has(repo.full_name) ? "checked" : ""}
            >
            <label class="form-check-label" for="${id}">${repo.full_name}</label>
        `;
        githubReposList.appendChild(div);

        div.querySelector("input").addEventListener("change", (e) => {
            if (e.target.checked) {
                selectedRepos.add(repo.full_name);
            } else {
                selectedRepos.delete(repo.full_name)
            }
        })
    });

    renderPagination(totalPages);
}


/**
 * Renders the pagination control for navigating through pages.
 */
function renderPagination(totalPages) {
    githubRepoPagination.innerHTML = "";

    // Botón Anterior
    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
    prevLi.innerHTML = `<a class="page-link" href="#">Previous</a>`;
    prevLi.addEventListener("click", (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            currentPage--;
            renderRepos();
        }
    });
    githubRepoPagination.appendChild(prevLi);

    // Texto página actual / total
    const pageInfo = document.createElement("li");
    pageInfo.className = "page-item disabled";
    pageInfo.innerHTML = `<span class="page-link">${currentPage} / ${totalPages}</span>`;
    githubRepoPagination.appendChild(pageInfo);

    // Botón Siguiente
    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${currentPage === totalPages ? "disabled" : ""}`;
    nextLi.innerHTML = `<a class="page-link" href="#">Next</a>`;
    nextLi.addEventListener("click", (e) => {
        e.preventDefault();
        if (currentPage < totalPages) {
            currentPage++;
            renderRepos();
        }
    });
    githubRepoPagination.appendChild(nextLi);
}


/* Fetch repos from the server and render them */
fetch("/plugins/github_backup/repos")
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                throw new Error("User not authenticated with GitHub. Please install the app or make sure you have the necessary permissions.");
            }
            if (response.status === 500) {
                throw new Error("An unexpected error ocurred while attempting to connect to GitHub. Please check the GitHubApp settings and your Internet connection.");
            }
            return response.json().then(err => {
                throw new Error(err.message || "Unexpected error communicating with the API.");
          });
        }
        return response.json();
        })
    .then(data => {
        if (!data.success) {
            throw new Error(data.message || "The API did not respond successfully.");
        }

        allRepos = data.repos || [];

        if (githubLoginSection) githubLoginSection.style.display = "none";
        if (githubReposSection) githubReposSection.style.display = "block";
        const errorSection = document.getElementById("github-error-section");
        if (errorSection) errorSection.style.display = "none";

        renderRepos();
        loadSavedRepos();
    })
    .catch(error => {
        console.error("Error fetching the repos: ", error);
        const errorSection = document.querySelector("#github-error-section");
        const errorMessage = document.querySelector("#github-error-message");
        if (errorMessage) errorMessage.textContent = error.message;
        if (errorSection) errorSection.style.display = "block";
        if (githubLoginSection) githubLoginSection.style.display = "block";
        if (githubReposSection) githubReposSection.style.display = "none";
    });


/* Save selected repos  */
buttonSaveSelectedRepos?.addEventListener("click", () => {
    const selected = Array.from(selectedRepos).map(name => {
        return allRepos.find(r => r.full_name === name);
    }).filter(Boolean);

    if (selected.length === 0) {
        alert("No repositories selected");
        return;
    }

    fetch("/plugins/github_backup/repos/selection", {
        method: "POST",
        credentials: "same-origin",
        headers: {
            "Content-Type": "application/json",
            "CSRF-Token": CTFd.config.csrfNonce
        },
        body: JSON.stringify({ repos: selected })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("Repositories saved successfully.");
            loadSavedRepos();
        } else {
            alert("Error saving: " + data.message || "Unexpected error.");
        }
    })
    .catch(err => {
        alert("Unexpected Error: " + err.message);
    });
});


/**
 * Loads the saved repositories and updates the UI with the list of repositories retrieved.
 */
function loadSavedRepos() {
    const tableBody = document.querySelector("#github-saved-repos-table tbody");
    const paginationContainer = document.querySelector("#github-saved-repos-pagination");

    tableBody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center">
          <i class="fas fa-spinner fa-spin text-warning"></i>
          <div class="small text-muted">Loading saved repositories...</div>
        </td>
      </tr>
    `;

    fetch("/plugins/github_backup/repos/saved", {
        method: "GET",
        credentials: "same-origin"
    })
    .then(r => r.json())
    .then(data => {
        tableBody.innerHTML = "";

        if (!data.success) {
            tableBody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">ERROR: ${data.message || "Could not load the repositories."}</td></tr>`;
            return;
        }

        const previousSelection = new Set(selectedSavedRepos);
        savedRepos = data.repos || [];
        savedReposPage = 1;
        selectedSavedRepos = new Set([...previousSelection].filter(id => savedRepos.some(r => String(r.id) === id)));

        renderSavedRepos();
    })
    .catch(err => {
        tableBody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">Error: ${err.message}</td></tr>`;
    });
}

function renderSavedRepos() {
    const tableBody = document.querySelector("#github-saved-repos-table tbody");
    const paginationContainer = document.querySelector("#github-saved-repos-pagination");

    tableBody.innerHTML = "";

    if (savedRepos.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No saved repositories.</td></tr>`;
        return;
    }

    const totalPages = Math.ceil(savedRepos.length / SAVED_ITEMS_PER_PAGE);
    const start = (savedReposPage - 1) * SAVED_ITEMS_PER_PAGE;
    const end = start + SAVED_ITEMS_PER_PAGE;
    const reposToShow = savedRepos.slice(start, end);

    // Renderizamos filas
    reposToShow.forEach(repo => {
        const tr = document.createElement("tr");

        const checkedAttr = selectedSavedRepos.has(String(repo.id)) ? "checked" : "";

        tr.innerHTML = `
            <td>
                <input 
                    type="checkbox" 
                    class="sync-checkbox" 
                    value="${repo.id}"
                    ${checkedAttr}
                >
            </td>
            <td>${repo.full_name}</td>
            <td>${repo.last_synced_at ? repo.last_synced_at + " UTC" : "-"}</td>
            <td>
                <button class="btn btn-sm btn-warning sync-now-btn" data-id="${repo.id}">
                    <i class="fas fa-download me-1"></i> ${repo.selected ? "Update" : "Import"}
                </button>
                <button class="btn btn-sm btn-danger delete-repo-btn" data-id="${repo.id}">
                    <i class="fas fa-trash me-1"></i> Delete
                </button>
            </td>
        `;
        tableBody.appendChild(tr);
    });

    // ✅ Aquí está la clave:
    // Escuchar cambios de checkbox y actualizar el Set global
    tableBody.querySelectorAll(".sync-checkbox").forEach(cb => {
        cb.addEventListener("change", e => {
            const id = String(e.target.value);
            if (e.target.checked) {
                selectedSavedRepos.add(id);
            } else {
                selectedSavedRepos.delete(id);
            }
        });

        // Aseguramos que el estado visual sea correcto incluso si se volvió a renderizar
        if (selectedSavedRepos.has(String(cb.value))) {
            cb.checked = true;
        }
    });

    // Paginación
    renderSavedReposPagination(totalPages);

    // Reasignar los listeners de botones
    attachRepoEventListeners();
}

function renderSavedReposPagination(totalPages) {
    const pagination = document.querySelector("#github-saved-repos-pagination");
    pagination.innerHTML = "";

    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${savedReposPage === 1 ? "disabled" : ""}`;
    prevLi.innerHTML = `<a class="page-link" href="#">Previous</a>`;
    prevLi.addEventListener("click", e => {
        e.preventDefault();
        if (savedReposPage > 1) {
            savedReposPage--;
            renderSavedRepos();
        }
    });
    pagination.appendChild(prevLi);

    const infoLi = document.createElement("li");
    infoLi.className = "page-item disabled";
    infoLi.innerHTML = `<span class="page-link">${savedReposPage} / ${totalPages}</span>`;
    pagination.appendChild(infoLi);

    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${savedReposPage === totalPages ? "disabled" : ""}`;
    nextLi.innerHTML = `<a class="page-link" href="#">Next</a>`;
    nextLi.addEventListener("click", e => {
        e.preventDefault();
        if (savedReposPage < totalPages) {
            savedReposPage++;
            renderSavedRepos();
        }
    });
    pagination.appendChild(nextLi);
}


/**
 * Attaches event listeners to various elements associated with repository management, 
 * such as buttons for deleting repositories, syncing repositories, and importing multiple repositories.
 */
function attachRepoEventListeners() {
    document.querySelectorAll(".delete-repo-btn").forEach(btn => {
        btn.onclick = () => {
            const repoId = btn.dataset.id;
            if (!confirm("Are you sure you want to delete this repository?")) return;

            fetch(`/plugins/github_backup/repos/${repoId}`, {
                method: "DELETE",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json", "CSRF-Token": CTFd.config.csrfNonce }
            })
            .then(r => r.json())
            .then(resp => {
                if (resp.success) {
                    alert("Deleted: " + resp.message);
                    loadSavedRepos();
                    loadAllChallenges();
                } else {
                    alert("Error: " + resp.message);
                }
            });
        };
    });
    
    document.querySelectorAll(".sync-now-btn").forEach(btn => {
        btn.onclick = async () => {
            if (isImportingRepos) return;
            isImportingRepos = true;

            const repoId = btn.dataset.id;
            const deleteModeChecked = document.querySelector('input[name="delete-mode"]:checked');
            const deleteModeValue = deleteModeChecked ? deleteModeChecked.value : false;

            if (!confirm("Are you sure you want to import the challenges from this repository?")) {
                isImportingRepos = false;
                return;
            }

            const row = btn.closest("tr");
            const syncCell = row.querySelector("td:nth-child(3)");
            const deleteBtn = row.querySelector(".delete-repo-btn");
            const originalSyncContent = syncCell.innerHTML;

            // Spinner
            syncCell.innerHTML = `<div class="text-center"><i class="fas fa-spinner fa-spin text-warning"></i><div class="small text-muted">Importing...</div></div>`;
            btn.disabled = true;
            deleteBtn.disabled = true;

            try {
                const resp = await fetch(`/plugins/github_backup/repos/${repoId}/import`, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "CSRF-Token": CTFd.config.csrfNonce },
                    body: JSON.stringify({ delete_mode: deleteModeValue })
                }).then(r => r.json());

                if (!resp.success) throw new Error(resp.message || "Import failed");

                let message = resp.message;
                if (resp.errors && resp.errors.length > 0) {
                    message += "\nErrors:\n" + resp.errors.map(e => `- ${e.file}: ${e.error}`).join("\n");
                }
                alert("Import complete:\n" + message);

                loadSavedRepos();
                loadAllChallenges();
            } catch (err) {
                alert("Unexpected Error: Check if the repository follows the expected format. " + err.message);
                syncCell.innerHTML = originalSyncContent;
            } finally {
                btn.disabled = false;
                deleteBtn.disabled = false;
                syncCell.innerHTML = originalSyncContent;
                isImportingRepos = false;
            }
        };
    });
    
    
    const importSelectedBtn = document.querySelector("#import-selected-repos");
    if (importSelectedBtn) {
        importSelectedBtn.onclick = async () => {
            if (isImportingRepos) return;
            const checkboxes = document.querySelectorAll(".sync-checkbox:checked");
            if (checkboxes.length === 0) {
                alert("No repositories selected.\nSelect at least one repository to import.");
                return;
            }
            if (!confirm(`You will import ${checkboxes.length} repositories. Continue?`)) return;

            isImportingRepos = true;
            const deleteModeChecked = document.querySelector('input[name="delete-mode"]:checked');
            const deleteModeValue = deleteModeChecked ? deleteModeChecked.value : false;

            for (const cb of checkboxes) {
                const repoId = cb.value;
                const row = cb.closest("tr");
                const syncCell = row.querySelector("td:nth-child(3)");
                const deleteBtn = row.querySelector(".delete-repo-btn");
                const btn = row.querySelector(".sync-now-btn");
                const originalSyncContent = syncCell.innerHTML;

                // Spinner
                syncCell.innerHTML = `<div class="text-center"><i class="fas fa-spinner fa-spin text-warning"></i><div class="small text-muted">Importing...</div></div>`;
                btn.disabled = true;
                deleteBtn.disabled = true;

                try {
                    const resp = await fetch(`/plugins/github_backup/repos/${repoId}/import`, {
                        method: "POST",
                        credentials: "same-origin",
                        headers: { "Content-Type": "application/json", "CSRF-Token": CTFd.config.csrfNonce },
                        body: JSON.stringify({ delete_mode: deleteModeValue })
                    }).then(r => r.json());

                    if (!resp.success) throw new Error(resp.message || "Import failed");

                    let message = resp.message;
                    if (resp.errors && resp.errors.length > 0) {
                        message += "\nErrors:\n" + resp.errors.map(e => `- ${e.file}: ${e.error}`).join("\n");
                    }
                    alert(`Imported ${repoId}: ${message}`);
                } catch (err) {
                    alert(`Error importing ${repoId}: ${err.message}`);
                    syncCell.innerHTML = originalSyncContent;
                } finally {
                    btn.disabled = false;
                    deleteBtn.disabled = false;
                    syncCell.innerHTML = originalSyncContent;
                }
            }

            loadSavedRepos();
            loadAllChallenges();
            isImportingRepos = false;
        };
    }
}

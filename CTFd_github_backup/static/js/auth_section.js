const bottonLinkInstalation = document.querySelector("#button-link-instalation");

// Complete instalation. Get de installation id
bottonLinkInstalation?.addEventListener("click", () => {
  fetch("/plugins/github_backup/installations", {
    method: "GET",
    credentials: "same-origin",
    headers: {
      "CSRF-Token": CTFd.config.csrfNonce
    }
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        confirm("Linked successfully. " + data.message);
        location.reload();
      } else {
        alert("Error: " + (data.message || "Unexpected error"));
      }
    })
    .catch((err) => {
      alert("Unexpected Error: " + err.message);
    });
});
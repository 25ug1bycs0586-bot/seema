document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.querySelector("[data-resume-file]");
  const dropZone = document.querySelector("[data-drop-zone]");
  const fileLabel = document.querySelector("[data-file-label]");

  const updateFileLabel = () => {
    if (fileInput && fileLabel) {
      fileLabel.textContent = fileInput.files.length ? fileInput.files[0].name : "Drop your file here or browse files";
    }
  };

  if (fileInput && dropZone) {
    fileInput.addEventListener("change", updateFileLabel);
    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
      });
    });
    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");
      });
    });
    dropZone.addEventListener("drop", (event) => {
      if (event.dataTransfer.files.length) {
        fileInput.files = event.dataTransfer.files;
        updateFileLabel();
      }
    });
    dropZone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        fileInput.click();
      }
    });
  }

  const form = document.querySelector("#analysis-form");
  if (form) {
    form.addEventListener("submit", () => {
      const button = form.querySelector("#analyze-button");
      const spinner = form.querySelector("[data-submit-spinner]");
      if (button) button.disabled = true;
      if (spinner) spinner.classList.remove("d-none");
      const label = form.querySelector("[data-button-label]");
      if (label) label.textContent = "Analyzing…";
    });
  }

  const role = new URLSearchParams(window.location.search).get("role");
  const roleSelect = document.querySelector("#target_role");
  if (role && roleSelect) {
    const option = Array.from(roleSelect.options).find((item) => item.value === role);
    if (option) roleSelect.value = option.value;
  }

  document.querySelectorAll("[data-learning-task]").forEach((checkbox) => {
    checkbox.addEventListener("change", async () => {
      const previous = !checkbox.checked;
      checkbox.disabled = true;
      try {
        const response = await fetch(checkbox.dataset.taskEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content,
          },
          body: JSON.stringify({ task_id: Number(checkbox.dataset.taskId), completed: checkbox.checked }),
        });
        if (!response.ok) throw new Error(`Saving progress failed (${response.status}).`);
        const status = document.querySelector("[data-task-status]");
        if (status) status.textContent = checkbox.checked ? "Task marked complete." : "Task marked incomplete.";
      } catch (error) {
        checkbox.checked = previous;
        const status = document.querySelector("[data-task-status]");
        if (status) status.textContent = `${error.message} Your change was not saved.`;
      } finally {
        checkbox.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-confirm-delete]").forEach((formToConfirm) => {
    formToConfirm.addEventListener("submit", (event) => {
      if (!window.confirm("Delete this report and its learning progress? This cannot be undone.")) {
        event.preventDefault();
      }
    });
  });

  const copyText = async (text, button) => {
    try {
      await navigator.clipboard.writeText(text);
      const original = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => { button.textContent = original; }, 1800);
    } catch {
      button.textContent = "Copy unavailable";
    }
  };

  document.querySelectorAll("[data-copy-summary]").forEach((button) => {
    button.addEventListener("click", () => {
      const summary = document.querySelector("[data-report-summary]");
      if (summary) copyText(summary.innerText, button);
    });
  });

  document.querySelectorAll("[data-copy-report]").forEach((button) => {
    button.addEventListener("click", () => {
      const page = document.querySelector(".main-content .page-container");
      if (page) copyText(page.innerText, button);
    });
  });
});

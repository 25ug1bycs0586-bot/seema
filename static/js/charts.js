document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-skill-chart]").forEach((canvas) => {
    if (!window.Chart) {
      const message = document.createElement("p");
      message.className = "small text-secondary";
      message.textContent = "The chart could not load; skill details are listed beside it.";
      canvas.replaceWith(message);
      return;
    }
    const labels = JSON.parse(canvas.dataset.labels || "[]");
    const values = JSON.parse(canvas.dataset.values || "[]");
    new window.Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: ["#635bdb", "#3f75d5", "#36a885", "#e7a54a", "#db6d8b", "#9d75c8"],
          borderWidth: 0,
          hoverOffset: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: "68%",
        plugins: {
          legend: { position: "bottom", labels: { usePointStyle: true, padding: 14, color: "#63708a" } },
          tooltip: { callbacks: { label: (context) => ` ${context.label}: ${context.raw} skill(s)` } },
        },
      },
    });
  });
});

function blinkDot(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add("blinking");
  setTimeout(() => el.classList.remove("blinking"), 1500);
}

function updateMap(position, movingTo) {
  const dots = ["H", "A", "P", "B"];
  const lines = ["HA", "HP", "HB"];

  dots.forEach((dot) => {
    const dotEl = document.getElementById(`dot-${dot}`);
    if (dotEl) dotEl.classList.remove("active-dot");
  });

  lines.forEach((line) => {
    const lineEl = document.getElementById(`line-${line}`);
    if (lineEl) lineEl.classList.remove("active-line");
  });

  if (movingTo && movingTo !== "null") {
    const line = document.getElementById(`line-H${movingTo}`);
    if (line) line.classList.add("active-line");
  } else if (position) {
    const dot = document.getElementById(`dot-${position}`);
    if (dot) {
      dot.classList.add("active-dot");
      blinkDot(`dot-${position}`);
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const dotH = document.getElementById("dot-H");
  const targets = ["dot-A", "dot-P", "dot-B"];
  const lines = {
    "dot-A": document.getElementById("line-HA"),
    "dot-P": document.getElementById("line-HP"),
    "dot-B": document.getElementById("line-HB"),
  };

  dotH.addEventListener("dragstart", (e) => {
    e.dataTransfer.setData("text/plain", "dot-H");
  });

  targets.forEach((targetId) => {
    const target = document.getElementById(targetId);
    target.addEventListener("dragover", (e) => e.preventDefault());

    target.addEventListener("drop", (e) => {
      e.preventDefault();

      // Hide all lines
      Object.values(lines).forEach((line) => {
        if (line) line.style.display = "none";
      });

      // Show the line from H to dropped target
      const lineToShow = lines[targetId];
      if (lineToShow) lineToShow.style.display = "block";

      // Notify backend
      const positionLetter = targetId.slice(-1); // A, P, or B
      fetch("/update_place_position", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ position: positionLetter }),
      }).then(() => {
        alert(`H moved to ${positionLetter} position`);
      });
    });
  });
});

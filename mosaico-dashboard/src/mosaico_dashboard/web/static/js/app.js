// Sidebar collapse, remembered across pages and visits.
function toggleNav() {
  const collapsed = document.documentElement.classList.toggle("nav-collapsed");
  try {
    localStorage.setItem("nav", collapsed ? "collapsed" : "open");
  } catch (e) {}
}

// Copy the last row of a container, with empty inputs (key/value rows in forms).
function addRow(containerId) {
  const container = document.getElementById(containerId);
  const row = container.lastElementChild.cloneNode(true);
  row.querySelectorAll("input").forEach((input) => (input.value = ""));
  container.appendChild(row);
  row.querySelector("input").focus();
}

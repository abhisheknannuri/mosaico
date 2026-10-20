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

// Ingest file list: show the files whose path contains the search text (any case), with the
// match highlighted; an empty search shows every file again.
function filterFiles(input) {
  const query = input.value.trim().toLowerCase();
  const panel = input.closest(".files-panel");
  const rows = panel.querySelectorAll(".file-list li[data-name]");
  let shown = 0;
  rows.forEach((row) => {
    const name = row.dataset.name;
    const target = row.querySelector(".file-name");
    target.dataset.html ??= target.innerHTML;
    const index = query ? name.toLowerCase().indexOf(query) : 0;
    row.hidden = index === -1;
    if (index === -1) return;
    shown += 1;
    if (!query) {
      target.innerHTML = target.dataset.html;
      return;
    }
    const mark = document.createElement("mark");
    mark.textContent = name.slice(index, index + query.length);
    target.replaceChildren(
      document.createTextNode(name.slice(0, index)),
      mark,
      document.createTextNode(name.slice(index + query.length)),
    );
  });
  const count = panel.querySelector(".file-count");
  count.textContent = query ? `${shown} of ${rows.length} files` : `${rows.length} files`;
}

// Mark the clicked file as selected in its list.
function selectRow(link) {
  const list = link.closest(".file-list");
  list.querySelectorAll("li[aria-selected]").forEach((row) => row.removeAttribute("aria-selected"));
  link.closest("li").setAttribute("aria-selected", "true");
}

// Resizable Ingest workspace: drag the splitter; the width of the file panel is remembered.
function applyFilesWidth(root) {
  let width = null;
  try {
    width = localStorage.getItem("filesWidth");
  } catch (e) {}
  if (width) root.querySelectorAll(".workspace").forEach((w) => w.style.setProperty("--files-width", width));
}

function startResize(event) {
  const workspace = event.target.closest(".workspace");
  const left = workspace.getBoundingClientRect().left;
  const max = workspace.clientWidth * 0.7;
  event.preventDefault();
  const move = (e) => {
    const width = Math.min(max, Math.max(240, e.clientX - left));
    workspace.style.setProperty("--files-width", `${width}px`);
  };
  const stop = () => {
    document.removeEventListener("mousemove", move);
    document.removeEventListener("mouseup", stop);
    try {
      localStorage.setItem("filesWidth", workspace.style.getPropertyValue("--files-width"));
    } catch (e) {}
  };
  document.addEventListener("mousemove", move);
  document.addEventListener("mouseup", stop);
}

function showSelectedFile(root) {
  const row = root.querySelector(".file-list li[aria-selected]");
  if (row) row.scrollIntoView({ block: "nearest" });
}

document.addEventListener("DOMContentLoaded", () => {
  applyFilesWidth(document);
  showSelectedFile(document);
});
document.addEventListener("htmx:afterSwap", (event) => applyFilesWidth(event.detail.target.parentElement || document));

// Folder dialog: open it when its content arrives.
document.addEventListener("htmx:afterSwap", (event) => {
  const dialog = event.detail.target;
  if (dialog.id === "folder-dialog" && !dialog.open) dialog.showModal();
});

// Folder dialog: a click selects a row; only a folder can be chosen.
function pickEntry(row) {
  const dialog = row.closest(".folder-dialog");
  dialog.querySelector("[aria-selected]")?.removeAttribute("aria-selected");
  row.setAttribute("aria-selected", "true");
  const isFolder = row.dataset.folder === "true";
  dialog.querySelector("#folder-select").disabled = !isFolder;
  const status = dialog.querySelector("#folder-status");
  if (isFolder) {
    dialog.querySelector("#folder-selection").value = row.dataset.path;
    status.innerHTML = "Selected: <code></code>";
    status.querySelector("code").textContent = row.dataset.path;
  } else {
    status.textContent = "Files can't be chosen: select a folder.";
  }
}

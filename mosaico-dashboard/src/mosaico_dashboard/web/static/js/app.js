// Sidebar collapse, remembered across pages and visits.
function toggleNav() {
  const collapsed = document.documentElement.classList.toggle("nav-collapsed");
  try {
    localStorage.setItem("nav", collapsed ? "collapsed" : "open");
  } catch (e) {}
}

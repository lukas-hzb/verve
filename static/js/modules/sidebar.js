/** Desktop collapse preference and independent mobile navigation drawer. */
export class SidebarManager {
  constructor() {
    this.sidebar = document.querySelector(".sidebar");
    this.toggleButton = document.getElementById("sidebar-toggle");
    this.mobileToggle = document.getElementById("mobile-sidebar-toggle");
    this.backdrop = document.getElementById("sidebar-backdrop");
    this.content = document.getElementById("main-content");
    this.header = document.querySelector(".mobile-header");
    this.logo = this.sidebar?.querySelector(".logo_name");
    this.mobileQuery = window.matchMedia("(max-width: 768px)");
    this.mobileOpen = false;
    if (!this.sidebar || !this.toggleButton) return;
    this.toggleButton.addEventListener("click", () => this.toggle());
    this.mobileToggle.addEventListener("click", () => this.setMobileOpen(true));
    this.backdrop.addEventListener("click", () => this.setMobileOpen(false));
    this.sidebar.addEventListener("click", (event) => {
      if (this.mobileQuery.matches && event.target.closest("a"))
        this.setMobileOpen(false, false);
    });
    document.addEventListener("keydown", (event) => this.handleKeydown(event));
    this.mobileQuery.addEventListener("change", () =>
      this.setMobileOpen(false, false),
    );
    window.addEventListener("pageshow", () => this.setMobileOpen(false, false));
    this.updateState();
  }
  toggle() {
    if (this.mobileQuery.matches) {
      this.setMobileOpen(!this.mobileOpen);
      return;
    }
    this.sidebar.classList.toggle("close");
    const collapsed = this.sidebar.classList.contains("close");
    document.cookie = `sidebar_collapsed=${collapsed}; path=/; max-age=31536000; SameSite=Lax`;
    this.updateState();
  }
  setMobileOpen(open, restoreFocus = true) {
    const wasOpen = this.mobileOpen;
    this.mobileOpen = open && this.mobileQuery.matches;
    this.updateState();
    if (this.mobileOpen) {
      // Let the drawer become visible before focusing its close button.
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (this.mobileOpen) this.toggleButton.focus();
        });
      });
    } else if (wasOpen && restoreFocus && this.mobileQuery.matches)
      this.mobileToggle.focus();
  }
  updateState() {
    const mobile = this.mobileQuery.matches;
    const expanded = mobile
      ? this.mobileOpen
      : !this.sidebar.classList.contains("close");
    this.sidebar.classList.toggle("mobile-open", this.mobileOpen);
    document.body.classList.toggle("navigation-open", this.mobileOpen);
    this.sidebar.inert = mobile && !this.mobileOpen;
    this.content.inert = this.mobileOpen;
    this.header.inert = this.mobileOpen;
    this.mobileToggle.setAttribute("aria-expanded", String(this.mobileOpen));
    this.toggleButton.setAttribute("aria-expanded", String(expanded));
    this.toggleButton.setAttribute(
      "aria-label",
      mobile
        ? "Close Navigation"
        : expanded
          ? "Collapse Sidebar"
          : "Expand Sidebar",
    );
    this.logo.tabIndex = expanded ? 0 : -1;
    if (mobile)
      this.sidebar.setAttribute("aria-hidden", String(!this.mobileOpen));
    else this.sidebar.removeAttribute("aria-hidden");
    if (this.mobileOpen) {
      this.sidebar.setAttribute("role", "dialog");
      this.sidebar.setAttribute("aria-modal", "true");
    } else {
      this.sidebar.removeAttribute("role");
      this.sidebar.removeAttribute("aria-modal");
    }
  }
  handleKeydown(event) {
    if (!this.mobileOpen) return;
    if (event.key === "Escape") {
      event.preventDefault();
      this.setMobileOpen(false);
    } else if (event.key === "Tab") {
      const focusable = [...this.sidebar.querySelectorAll("a[href], button")];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }
}

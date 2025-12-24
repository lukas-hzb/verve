/**
 * Sidebar Module
 * Handles sidebar collapse/expand functionality and state persistence
 */

export class SidebarManager {
    constructor() {
        this.sidebar = document.querySelector(".sidebar");
        this.toggleButton = document.querySelector("#sidebar-toggle");

        this.init();
    }

    init() {
        if (!this.toggleButton) return;

        this.toggleButton.addEventListener("click", () => {
            this.toggle();
        });
    }

    toggle() {
        this.sidebar.classList.toggle("close");

        // Toggle icon text
        if (this.sidebar.classList.contains("close")) {
            this.toggleButton.textContent = 'menu';
        } else {
            this.toggleButton.textContent = 'menu_open';
        }

        const isCollapsed = this.sidebar.classList.contains("close");
        this.saveSidebarState(isCollapsed);
    }

    saveSidebarState(isCollapsed) {
        // Set cookie that expires in one year
        const maxAge = 365 * 24 * 60 * 60; // 1 year in seconds
        document.cookie = `sidebar_collapsed=${isCollapsed}; path=/; max-age=${maxAge}; SameSite=Lax`;
    }
}

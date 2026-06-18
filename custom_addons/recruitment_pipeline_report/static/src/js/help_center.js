/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useRef, useState, onMounted } from "@odoo/owl";
import { Component, xml } from "@odoo/owl";

/**
 * HelpCenterPanel — slide-in panel rendered inside the systray.
 * Clicking the ? button toggles the full-screen overlay.
 */

class HelpCenterDialog extends Component {
    static template = "recruitment_pipeline_report.HelpCenterDialog";
    static props = { onClose: Function };

    setup() {
        this.state = useState({ activePage: "overview" });
    }

    show(page) {
        this.state.activePage = page;
    }

    isActive(page) {
        return this.state.activePage === page;
    }
}

class HelpCenterSystray extends Component {
    static template = "recruitment_pipeline_report.HelpCenterSystray";

    setup() {
        this.state = useState({ open: false });
    }

    toggle() {
        this.state.open = !this.state.open;
    }

    close() {
        this.state.open = false;
    }
}

HelpCenterSystray.components = { HelpCenterDialog };

registry.category("systray").add("recruitment_help_center", {
    Component: HelpCenterSystray,
    sequence: 5,
});

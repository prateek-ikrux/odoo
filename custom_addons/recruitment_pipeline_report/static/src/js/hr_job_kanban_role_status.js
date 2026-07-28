/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { CANCEL_GLOBAL_CLICK, KanbanRecord } from "@web/views/kanban/kanban_record";

patch(KanbanRecord.prototype, {
    onGlobalClick(ev, newWindow) {
        const { record, getSelection } = this.props;
        const isClosedJob = record.resModel === "hr.job" && record.data.x_role_status === "closed";
        // Mirror the base method's own guards (link/button clicks, multi-select)
        // so we only intercept the click that would actually open the pipeline,
        // and let explicit actions like "Configure" go through untouched.
        if (
            isClosedJob &&
            !ev.target.closest(CANCEL_GLOBAL_CLICK) &&
            getSelection().length === 0 &&
            !ev.altKey
        ) {
            this.notification.add(
                _t("This requirement is Closed. New Profiles cannot be added."),
                { type: "warning" }
            );
            return;
        }
        return super.onGlobalClick(ev, newWindow);
    },
});

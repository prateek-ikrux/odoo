/**
 * Before an opportunity is saved with a client name or engagement type new to
 * it, ask the server what CRM already holds for that client or a like-named
 * one (crm.lead.get_client_duplicate_message). If anything, a popup lists it
 * and the user saves anyway or discards the changes; closing the popup goes
 * back to editing. Nothing is refused.
 *
 * Patched on Record rather than on CRM's form view so that an opportunity
 * edited in a form dialog, or on the kanban's quick-create card should that be
 * switched back on, is checked too: both build their form with the plain form
 * model, which a view of our own would miss. Only the root crm.lead record of a
 * view is checked, so the POC lines inside the form and every other model save
 * as before. A form with a required field still empty gets Odoo's own message
 * first, and the popup on the save after. An urgent save - the browser tab
 * closing - has no time for a popup and goes through unchecked.
 */
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { Record } from "@web/model/relational_model/record";

patch(Record.prototype, {
    async _save() {
        if (
            this.resModel === "crm.lead" &&
            this.config.isRoot &&
            !this.model._urgentSave &&
            (this.isNew || "name" in this._changes || "engagement_type" in this._changes) &&
            this._checkValidity({ silent: true }) &&
            !(await this._crmConfirmClientDuplicates())
        ) {
            return false;
        }
        return super._save(...arguments);
    },

    /**
     * @returns {Promise<boolean>} whether to go on with the save
     */
    async _crmConfirmClientDuplicates() {
        const { name, engagement_type, type, company_id } = this.data;
        const message = await this.model.orm.call("crm.lead", "get_client_duplicate_message", [], {
            name: name || false,
            engagement_type: engagement_type || false,
            lead_type: type || false,
            company_id: company_id?.id || false,
            lead_id: this.resId || false,
        });
        if (!message) {
            return true;
        }
        return new Promise((resolve) => {
            this.model.dialog.add(
                ConfirmationDialog,
                {
                    title: _t("Possible duplicate opportunity"),
                    body: message,
                    confirmLabel: _t("Save Anyway"),
                    confirm: () => resolve(true),
                    cancelLabel: _t("Discard Changes"),
                    cancel: () => {
                        this._discard();
                        resolve(false);
                    },
                    dismiss: () => resolve(false),
                },
                { onClose: () => resolve(false) }
            );
        });
    },
});

/**
 * Makes the Sales dropdown on a user's Access Rights page read-only, so the
 * CRM role beside it is the only place a sales right is chosen.
 *
 * Odoo already derives the Sales value: every CRM role implies its matching
 * sales_team group, and the stock widget shows an implied group as greyed
 * placeholder text and drops the options below it from the list. What it does
 * not do is stop someone picking an option *above* it - a BDA can be handed
 * Administrator on the Sales dropdown while the CRM dropdown still says BDA.
 * That grants delete on crm.lead, which the role matrix says no role below
 * Admin has.
 *
 * The page has no arch to attach readonly="1" to: `res_user_group_ids` reads
 * res.groups._get_view_group_hierarchy() and writes the fields itself. So the
 * server flags the privilege (models/res_groups.py) and the two patches below
 * are the two halves of honouring that flag - one to generate the field
 * read-only, one to give it something to show once it is.
 */
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

// Imported for the side effect: both widgets have to be in the registry before
// this file can reach for them, and nothing else here imports them.
import "@web/webclient/res_user_group_ids_field/res_user_group_ids_field";
import "@web/webclient/res_user_group_ids_field/res_user_group_ids_privilege_field";

const fields = registry.category("fields");

patch(fields.get("res_user_group_ids").component.prototype, {
    getPrivilegeArch(privilege) {
        if (!privilege.readonly) {
            return super.getPrivilegeArch(privilege);
        }
        const fieldName = this.getFieldName(privilege);
        return `<field name="${fieldName}" widget="res_user_group_ids_privilege" readonly="1"/>`;
    },
});

patch(fields.get("res_user_group_ids_privilege").component.prototype, {
    /**
     * What the read-only field shows in place of the select.
     *
     * A read-only SelectionField renders the label of its value, and the value
     * here is almost always false - a group that is merely implied by another
     * privilege is not in the user's own group_ids, which is the whole reason
     * the stock widget shows it as a placeholder rather than a value. Reading
     * the label off the value would therefore render a blank line for every
     * user who has a role.
     */
    get readonlyDisplayName() {
        const groupId = this.props.record.data[this.props.name];
        if (groupId) {
            // Set outright, which happens when a sales group was granted
            // directly rather than through a CRM role.
            return this.groups[groupId] ? this.groups[groupId].name : "";
        }
        if (this.impliedGroup) {
            return this.impliedGroupDisplayName;
        }
        // Neither set nor implied: no role, so the privilege's own placeholder
        // ("No" for Sales), which is the first option of the generated field.
        const [value, label] = this.props.record.fields[this.props.name].selection[0];
        return value === false ? label : "";
    },
});

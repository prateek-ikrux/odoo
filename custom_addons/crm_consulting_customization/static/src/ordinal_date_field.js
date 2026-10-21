/**
 * A date field that reads "21st July 2024".
 *
 * Neither strftime nor Luxon has a token for the ordinal suffix - `%d` and `d`
 * both give "21" - so a language's date_format cannot express this and the
 * string has to be built by hand.
 *
 * Only the *displayed* string changes. DateTimeField funnels every rendering
 * through getFormattedValue(), and its template already draws a focused field
 * as a real <input> and everything else (read-only, and an unfocused editable
 * field) as text. Overriding the one method therefore leaves typing, parsing
 * and the date picker exactly as Odoo ships them.
 *
 * The numeric argument is honoured rather than overridden: the template passes
 * it for the hover tooltip, which is there to give the unambiguous numeric date
 * and is the one place the long form would not help.
 */
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { DateTimeField, dateField } from "@web/views/fields/datetime/datetime_field";

/**
 * 1st, 2nd, 3rd, 4th ... and 11th, 12th, 13th, which are the exceptions to the
 * digit rule rather than followers of it.
 */
function ordinalSuffix(day) {
    if (day >= 11 && day <= 13) {
        return "th";
    }
    return { 1: "st", 2: "nd", 3: "rd" }[day % 10] || "th";
}

export class OrdinalDateField extends DateTimeField {
    getFormattedValue(valueIndex, numeric = this.props.numeric) {
        const value = this.values[valueIndex];
        if (numeric || !value || this.field.type !== "date") {
            return super.getFormattedValue(valueIndex, numeric);
        }
        return `${value.day}${ordinalSuffix(value.day)} ${value.monthLong} ${value.year}`;
    }
}

export const ordinalDateField = {
    ...dateField,
    component: OrdinalDateField,
    displayName: _t("Date (21st July 2024)"),
    // "21st September 2024" is the longest this gets, and the stock date width
    // is sized for "09/21/2024".
    listViewWidth: 150,
};

registry.category("fields").add("ordinal_date", ordinalDateField);

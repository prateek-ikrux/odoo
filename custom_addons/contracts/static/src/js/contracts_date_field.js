import { registry } from "@web/core/registry";
import {
    DateTimeField,
    dateField,
    dateTimeField,
} from "@web/views/fields/datetime/datetime_field";

// Contract dates are always read and typed as day/month/two-digit year,
// whatever the user's language says. The stock widget shortens them to
// "Jun 23" - or "Jun 23, 2027" outside the current year - instead.
const FORMATS = {
    date: "dd/MM/yy",
    datetime: "dd/MM/yy HH:mm",
};

export class ContractsDateField extends DateTimeField {
    get displayFormat() {
        return FORMATS[this.field.type];
    }

    setup() {
        // The stock field gives its date picker no way to take a format, so the
        // input would still show and parse the language's one while editing.
        // The picker is created synchronously inside the parent setup, so the
        // service is wrapped just for that call to hand it ours.
        const pickerService = this.env.services.datetime_picker;
        const create = pickerService.create;
        const format = this.displayFormat;
        pickerService.create = (params) =>
            create.call(pickerService, Object.assign(Object.create(params), { format }));
        try {
            super.setup();
        } finally {
            pickerService.create = create;
        }
    }

    getFormattedValue(valueIndex) {
        const value = this.values[valueIndex];
        return value ? value.toFormat(this.displayFormat) : "";
    }
}

registry.category("fields").add("contracts_date", {
    ...dateField,
    component: ContractsDateField,
    displayName: "Contract Date (dd/mm/yy)",
});
registry.category("fields").add("contracts_datetime", {
    ...dateTimeField,
    component: ContractsDateField,
    displayName: "Contract Date & Time (dd/mm/yy)",
});

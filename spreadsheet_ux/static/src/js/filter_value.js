/** @odoo-module **/

import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { _lt } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";

const EXTENDED_RELATIVE_DATE_RANGE_TYPES = [
    ...RELATIVE_DATE_RANGE_TYPES,
    { type: "today", description: _lt("Today") },
];

patch(FilterValue.prototype, 'spreadsheet_ux.FilterValue', {
    setup() {
        this._super.apply(this, arguments);
        this.relativeDateRangesTypes = EXTENDED_RELATIVE_DATE_RANGE_TYPES;
    },
});

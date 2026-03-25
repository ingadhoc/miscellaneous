/** @odoo-module **/
/**
 * Patches all company_dependent-aware field types with the building-icon button
 * and fallback CSS class.
 *
 * When a field has `company_dependent: true` in the model definition:
 *   1. Injects a CompanyDependentButton (fa-building-o) next to the input.
 *   2. Applies the CSS class `o_cd_fallback` when the value comes from the
 *      global fallback (no specific key set for the current company in the JSON).
 *
 * A single `makeCDPatch()` factory produces the identical mixin for every
 * field type, keeping the logic in one place.
 */

import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { CharField } from "@web/views/fields/char/char_field";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { FloatField } from "@web/views/fields/float/float_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { MonetaryField } from "@web/views/fields/monetary/monetary_field";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { CompanyDependentButton } from "./company_dependent_button";

// ─────────────────────────────────────────────────────────────────────────────
// Shared mixin factory
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Returns the patch object to apply to a field prototype.
 * Hooks (useService / useState) are always called unconditionally to comply
 * with OWL's hook ordering rules.
 */

function makeCDPatch() {
    return {
        setup() {
            super.setup();
            this._cdService = useService("company_dependent");
            this._cdState = useState({ isSpecific: null });
            if (this.isCompanyDependent) {
                onWillStart(() => this._loadCDMeta());
            }
        },

        /**
         * True when the field is marked as company_dependent in the model.
         */
        get isCompanyDependent() {
            return this.props.record?.fields?.[this.props.name]?.company_dependent === true;
        },

        /**
         * Fetches the isSpecific flag from the company_dependent service.
         * The service batches all CD fields for the same record into a single
         * SQL query and caches the result.
         */
        async _loadCDMeta() {
            const { resModel, resId } = this.props.record;
            if (!resId) return;
            const meta = await this._cdService.getMetaForRecord(resModel, resId);
            this._cdState.isSpecific = meta[this.props.name] ?? false;
        },
    };
}

// ─────────────────────────────────────────────────────────────────────────────
// Apply patches, register sub-component, and assign extended templates.
// ─────────────────────────────────────────────────────────────────────────────

const FIELDS = [
    Many2OneField,
    SelectionField,
    CharField,
    IntegerField,
    FloatField,
    MonetaryField,
    BooleanField,
    DateTimeField,
];

for (const Field of FIELDS) {
    patch(Field.prototype, makeCDPatch());
    Field.components = { ...Field.components, CompanyDependentButton };
}

// Each class points to its own extended template defined in templates.xml.
Many2OneField.template = "base_company_dependent.Many2OneField";
SelectionField.template = "base_company_dependent.SelectionField";
CharField.template = "base_company_dependent.CharField";
IntegerField.template = "base_company_dependent.IntegerField";
FloatField.template = "base_company_dependent.FloatField";
MonetaryField.template = "base_company_dependent.MonetaryField";
BooleanField.template = "base_company_dependent.BooleanField";
DateTimeField.template = "base_company_dependent.DateTimeField";

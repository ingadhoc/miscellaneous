/** @odoo-module **/
/**
 * Patches the Setting component used in res.config.settings views to replace
 * the static fa-building-o icon with an interactive CompanyDependentButton.
 *
 * This allows users to click the building icon in settings and see/edit
 * values per company, just like on regular form views.
 */

import { onMounted, onWillStart, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { Setting } from "@web/views/form/setting/setting";
import { SearchableSetting } from "@web/webclient/settings_form_view/settings/searchable_setting";
import { CompanyDependentButton } from "./company_dependent_button";

Setting.components = { ...Setting.components, CompanyDependentButton };
SearchableSetting.components = { ...SearchableSetting.components, CompanyDependentButton };

patch(Setting.prototype, {
    setup() {
        super.setup();
        this._cdService = useService("company_dependent");
        this._cdState = useState({ isSpecific: null, discoveredField: null });
        // Upstream's compiler sets `companyDependent` to `true` (boolean) when
        // the <setting> has `company_dependent="1"`, otherwise to the literal
        // string `"false"` (which is truthy in JS). Compare strictly to `true`
        // so the meta lookup/DOM discovery only runs on opted-in settings.
        if (this.props.companyDependent === true) {
            if (this.props.fieldName) {
                onWillStart(() => this._loadCDMeta());
            } else {
                // No fieldName from compiler: discover from DOM after mount
                onMounted(() => this._discoverFieldFromDOM());
            }
        }
    },

    /**
     * Override: suppress the static icon when we can show the interactive
     * button instead.
     */
    get displayCompanyDependentIcon() {
        if (this.displayCompanyDependentButton) {
            return false;
        }
        return super.displayCompanyDependentIcon;
    },

    /**
     * Whether to show the interactive CompanyDependentButton.
     *
     * Visible when company_dependent="1" is set on the <setting>, there is
     * more than one accessible company, and we can identify a target field —
     * either via the compiler-set labelString/fieldName, or via a field
     * discovered from the rendered DOM (covers settings where the first
     * child is not a <field>, e.g. document_layout_setting, default_taxes).
     */
    get displayCompanyDependentButton() {
        if (this.props.companyDependent !== true) return false;
        if (!this.props.record || user.allowedCompanies.length <= 1) return false;
        return Boolean(this.labelString || this.cdFieldName);
    },

    /**
     * Effective field name: from compiler prop or discovered from DOM.
     */
    get cdFieldName() {
        return this.props.fieldName || this._cdState.discoveredField || "";
    },

    /**
     * The field's label string.
     *
     * Falls back to the discovered field's string when the setting itself
     * has no labelString (settings whose first child is a wrapper div).
     */
    get cdFieldString() {
        if (this.labelString) return this.labelString;
        const fn = this.cdFieldName;
        const fieldDef = fn ? this.props.record?.fields?.[fn] : null;
        return fieldDef?.string || fn || "";
    },

    /**
     * Whether the field is required.
     */
    get cdFieldRequired() {
        const fn = this.cdFieldName;
        if (!this.props.record || !fn) return false;
        try {
            return this.props.record._isRequired(fn);
        } catch {
            return false;
        }
    },

    /**
     * Discover the first visible field widget name inside the setting DOM.
     * Called onMounted when the compiler didn't set a fieldName (cases where
     * the first child of <setting> is a wrapper div, not a <field>).
     *
     * Iterates over all .o_field_widget[name] descendants and picks the first
     * one that is actually rendered (offsetParent != null skips fields hidden
     * by `invisible=...` or by `groups=...` the user doesn't belong to).
     *
     * Uses the public `settingRef` only (set by upstream's Setting). If a
     * future Odoo refactors removes settingRef the discovery silently
     * degrades to "no button" — better than reaching into OWL's private
     * `__owl__.bdom.el` and breaking on every minor upgrade.
     */
    _discoverFieldFromDOM() {
        const el = this.settingRef?.el;
        if (!el) return;
        const widgets = el.querySelectorAll(".o_field_widget[name]");
        for (const widget of widgets) {
            if (widget.offsetParent !== null) {
                this._cdState.discoveredField = widget.getAttribute("name");
                this._loadCDMeta();
                return;
            }
        }
    },

    async _loadCDMeta() {
        const fn = this.cdFieldName;
        if (!fn) return;
        const { resModel, resId } = this.props.record;
        if (!resId) return;
        const meta = await this._cdService.getMetaForRecord(resModel, resId);
        this._cdState.isSpecific = meta[fn] ?? false;
    },

    async _onCDSaved() {
        await this.props.record.load();
        await this._loadCDMeta();
    },
});

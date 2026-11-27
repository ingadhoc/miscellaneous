/** @odoo-module **/
/**
 * Patches the Setting component used in res.config.settings views to replace
 * the static fa-building-o icon with an interactive CompanyDependentButton.
 *
 * This allows users to click the building icon in settings and see/edit
 * values per company, just like on regular form views.
 */

import { onMounted, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Setting } from "@web/views/form/setting/setting";
import { SearchableSetting } from "@web/webclient/settings_form_view/settings/searchable_setting";
import { CompanyDependentButton } from "./company_dependent_button";

Setting.components = { ...Setting.components, CompanyDependentButton };
SearchableSetting.components = { ...SearchableSetting.components, CompanyDependentButton };

patch(Setting.prototype, {
    setup() {
        super.setup();
        // `manageable` es null hasta que el servidor contesta, y la lista de
        // los que se pueden gestionar después. Con la lista vacía el bloque no
        // muestra nada: el ícono prometía algo que no existe.
        this._cdState = useState({ discoveredFields: [], manageable: null, failed: false });
        this.cdService = useService("company_dependent");
        // Upstream's compiler sets `companyDependent` to `true` (boolean) when
        // the <setting> has `company_dependent="1"`, otherwise to the literal
        // string `"false"` (which is truthy in JS). Compare strictly to `true`
        // so the DOM discovery only runs on opted-in settings.
        // No specific/default indicator here: the settings record is never
        // saved, and its targets are plain columns without a fallback.
        if (this.props.companyDependent === true) {
            onMounted(() => this._resolveManageableFields());
        }
    },

    /**
     * Pregunta al servidor cuáles de los campos del bloque varían por compañía.
     *
     * Un `<setting company_dependent="1">` cuyo único campo es un flag de
     * módulo (`module_account_inter_company_rules`) no tiene ningún valor por
     * compañía hasta que el módulo se instala y suma los suyos: hasta entonces
     * el bloque no muestra ícono.
     *
     * Si la consulta falla no se esconde nada: queda el ícono estático de Odoo.
     */
    async _resolveManageableFields() {
        this._discoverFieldsFromDOM();
        const candidates = this.cdCandidateFieldNames;
        if (!this.props.record || !candidates.length) {
            this._cdState.manageable = [];
            return;
        }
        const { resModel, resId } = this.props.record;
        try {
            const resolved = await this.cdService.resolveManageableFields(resModel, resId, candidates);
            const byName = new Map(resolved.map((f) => [f.field_name, f]));
            // La tanda contesta por todos los bloques: nos quedamos con los
            // nuestros, en el orden en que la vista los dibujó.
            this._cdState.manageable = candidates.filter((n) => byName.has(n)).map((n) => byName.get(n));
        } catch {
            this._cdState.failed = true;
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
        // Mientras resolvemos, y cuando el bloque no tiene ningún valor por
        // compañía, no va ícono. Si la consulta falló, queda el de Odoo.
        if (this.props.companyDependent === true && !this._cdState.failed) {
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
        return Boolean(this._cdState.manageable && this._cdState.manageable.length);
    },

    /**
     * Los campos del bloque que varían por compañía, ya resueltos: el diálogo
     * muestra una columna por cada uno.
     */
    get cdManageableFields() {
        return this._cdState.manageable || [];
    },

    /**
     * Effective field name: from compiler prop or discovered from DOM.
     */
    get cdFieldName() {
        return this.props.fieldName || this._cdState.discoveredFields[0] || "";
    },

    /**
     * Every field rendered inside the setting, in view order, starting with
     * the one the compiler picked. The button sends them to the server, which
     * answers which one can be managed per company: in blocks like
     * `Quotation Templates` that is not the first field but `Default Template`.
     */
    get cdCandidateFieldNames() {
        const names = [];
        for (const name of [this.props.fieldName, ...this._cdState.discoveredFields]) {
            if (name && !names.includes(name)) {
                names.push(name);
            }
        }
        return names;
    },

    /**
     * The field's label string.
     *
     * Falls back to the discovered field's string when the setting itself
     * has no labelString (settings whose first child is a wrapper div).
     */
    get cdFieldString() {
        // Con un solo campo gestionable, el diálogo se titula con ese campo
        // ("Default Template"); con varios, con el nombre del bloque.
        const manageable = this.cdManageableFields;
        if (manageable.length === 1) return manageable[0].field_string;
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
     * Discover the visible field widget names inside the setting DOM.
     *
     * Covers both settings whose first child is a wrapper div instead of a
     * <field>, and settings whose per-company value sits in a field further
     * down the block.
     *
     * Iterates over all .o_field_widget[name] descendants and keeps those
     * actually rendered (offsetParent != null skips fields hidden by
     * `invisible=...` or by `groups=...` the user doesn't belong to).
     *
     * Uses the public `settingRef` only (set by upstream's Setting). If a
     * future Odoo refactors removes settingRef the discovery silently
     * degrades to "no button" — better than reaching into OWL's private
     * `__owl__.bdom.el` and breaking on every minor upgrade.
     */
    _discoverFieldsFromDOM() {
        const el = this.settingRef?.el;
        if (!el) return;
        const names = [];
        for (const widget of el.querySelectorAll(".o_field_widget[name]")) {
            const name = widget.getAttribute("name");
            if (widget.offsetParent !== null && !names.includes(name)) {
                names.push(name);
            }
        }
        this._cdState.discoveredFields = names;
    },
});

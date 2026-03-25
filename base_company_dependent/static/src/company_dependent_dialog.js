/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * Diálogo de gestión multicompañía para campos company_dependent.
 *
 * Carga los valores por compañía desde el backend y permite:
 *   - Ver una estructura jerárquica (hasta 3 niveles) de compañías/sucursales.
 *   - Editar el valor por compañía (Many2One, Selection, Float, Boolean, Char, Date…).
 *   - Copiar (propagar) el valor de una compañía padre hacia todas sus hijas.
 *   - Vaciar explícitamente el campo (guarda ``false`` en el JSON).
 *   - Resetear la clave del JSON (restaura al fallback global).
 *
 * Análogo a TranslationDialog del módulo ``web``.
 */
export class CompanyDependentDialog extends Component {
    static template = "base_company_dependent.CompanyDependentDialog";
    static components = { Dialog, AutoComplete };
    static props = {
        fieldName: { type: String },
        fieldString: { type: String },
        required: { type: Boolean },
        resId: { type: Number },
        resModel: { type: String },
        onSaved: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.cdService = useService("company_dependent");
        this.notification = useService("notification");

        this.title = _t("Company Values: %s", this.props.fieldString);

        this.state = useState({
            rows: [],
            fieldType: null,
            comodelName: null,
            selectionOptions: [],
            /** Cambios pendientes: Map<company_id, {value_id, is_reset}> */
            changes: {},
            /** Counter per row to force AutoComplete re-render on revert */
            revertKeys: {},

        });

        onWillStart(() => this._loadValues());
    }

    // ---------------------------------------------------------------
    // Textos (getters para evitar problemas del tokenizador OWL con
    // caracteres especiales en expresiones de template)
    // ---------------------------------------------------------------

    get autoCompletePlaceholder() {
        return _t("No value (explicitly False)");
    }

    /**
     * Placeholder por fila: muestra el texto de "vaciar explícitamente" únicamente
     * cuando la fila no tiene ningún valor (ni específico ni fallback). Si tiene
     * un valor por defecto visible, el placeholder queda vacío para no solaparse.
     */
    getRowPlaceholder(row) {
        const effective = this._getEffectiveRow(row);
        if (effective.display_value) return "";
        return effective.is_specific ? this.autoCompletePlaceholder : "";
    }

    get resetButtonTitle() {
        return _t("Restore to default value (removes the JSON key)");
    }

    get copyButtonTitle() {
        return _t("Copy this value to all child companies");
    }

    get labelSpecific() {
        return _t("Specific");
    }

    get labelDefault() {
        return _t("Default");
    }

    get loadingText() {
        return _t("Loading company values...");
    }

    get footerNoteHtml() {
        return {
            reset: _t("Reset "),
            resetDesc: _t("removes the set value and restores to the global default value."),
            copy: _t("Copy "),
            copyDesc: _t("propagates the value of a parent company to all its child companies."),
        };
    }

    get labelCompany() {
        return _t("Company");
    }

    get labelValue() {
        return _t("Value");
    }

    get labelStatus() {
        return _t("Status");
    }

    get labelSave() {
        return _t("Save");
    }

    get labelCopy() {
        return _t("Copy");
    }

    get labelDiscard() {
        return _t("Discard");
    }

    // ---------------------------------------------------------------
    // Carga de datos
    // ---------------------------------------------------------------

    async _loadValues() {
        const { resModel, resId, fieldName } = this.props;
        const result = await this.orm.call(
            "base.company.dependent",
            "get_company_dependent_values",
            [resModel, resId, fieldName],
        );
        this.state.rows = result.values.map((row) => ({ ...row }));
        this.state.fieldType = result.field_type;
        this.state.comodelName = result.comodel_name;
        this.state.selectionOptions = result.selection_options || [];
    }

    // ---------------------------------------------------------------
    // Helpers de jerarquía
    // ---------------------------------------------------------------

    /**
     * Construye el árbol ordenado para renderizar en el template.
     * Devuelve una lista plana donde cada elemento tiene {row, depth, isFirst, isLast}
     * pero ordenada de forma que padre precede a sus hijos.
     */
    get orderedRows() {
        const rows = this.state.rows;
        if (!rows.length) return [];

        // Pre-build parent_id → children map for O(n) traversal
        const childrenMap = {};
        for (const row of rows) {
            childrenMap[row.company_id] = [];
        }
        for (const row of rows) {
            if (row.parent_id != null && childrenMap[row.parent_id]) {
                childrenMap[row.parent_id].push(row);
            }
        }

        const roots = rows.filter((r) => r.level === 1);
        const result = [];

        const addRow = (row, depth) => {
            result.push({ row, depth });
            for (const child of childrenMap[row.company_id]) {
                addRow(child, depth + 1);
            }
        };

        for (const root of roots) {
            addRow(root, 0);
        }

        return result;
    }

    // ---------------------------------------------------------------
    // Estado derivado por fila
    // ---------------------------------------------------------------

    /**
     * Devuelve el estado efectivo de una fila, combinando el original con
     * los cambios pendientes.
     */
    _getEffectiveRow(row) {
        const change = this.state.changes[row.company_id];
        if (!change) return row;
        if (change.is_reset) {
            return {
                ...row,
                is_specific: false,
                value_id: row.fallback_value_id ?? null,
                display_value: row.fallback_display_value ?? null,
            };
        }
        return {
            ...row,
            is_specific: true,
            value_id: change.value_id,
            display_value: change.display_value,
        };
    }

    isSpecificRow(row) {
        return this._getEffectiveRow(row).is_specific;
    }

    getDisplayValue(row) {
        return this._getEffectiveRow(row).display_value || "";
    }

    // ---------------------------------------------------------------
    // Interacción del usuario
    // ---------------------------------------------------------------

    /**
     * Returns a unique key for the AutoComplete component of a given row.
     * Incrementing this key forces OWL to destroy and re-create the component,
     * which is needed when reverting changes on required fields so the input
     * text goes back to the effective display value.
     */
    getAutoCompleteKey(row) {
        return `ac-${row.company_id}-${this.state.revertKeys[row.company_id] || 0}`;
    }

    /**
     * Genera las sources para el componente AutoComplete de una fila.
     *
     * El domain pasado a name_search combina:
     *   - El domain estático del campo original (ej. filtro por tipo de cuenta).
     *   - El domain de compañía: comodel._check_company_domain(company).
     * Ambos vienen pre-calculados desde el backend en `row.domain`.
     *
     * IMPORTANTE: en la API de AutoComplete el callback de selección va en cada
     * opción como `onSelect()`, NO como prop del componente.
     */
    getAutoCompleteSources(row) {
        const self = this;
        // Usamos el domain efectivo calculado por el backend para esta fila.
        // Fallback a [] si la fila no lo trae (p.ej. campos no-many2one).
        const effectiveDomain = row.domain || [];
        return [
            {
                options: async (search) => {
                    if (!self.state.comodelName) return [];
                    const results = await self.orm.call(
                        self.state.comodelName,
                        "name_search",
                        [],
                        { name: search, domain: effectiveDomain, limit: 10 },
                    );
                    return results.map(([id, label]) => ({
                        value: id,
                        label,
                        onSelect: () => self.onSelectValue(row, { value: id, label }),
                    }));
                },
            },
        ];
    }

    /**
     * Callback del prop `onChange` del AutoComplete.
     * AutoComplete lo llama al hacer blur con { inputValue, isOptionSelected }.
     * Cuando el usuario borra el texto y sale sin seleccionar → vaciado explícito.
     */
    onAutoCompleteChange(row, info) {
        if (!info.inputValue && !info.isOptionSelected) {
            if (!this.props.required) {
                this.onClearValue(row);
            } else {
                // Campo required: no se puede vaciar. Revertimos cualquier cambio
                // pendiente para esta fila y notificamos al usuario.
                delete this.state.changes[row.company_id];
                // Bump the revert key to force AutoComplete to re-render with the
                // original (or fallback) display value.
                this.state.revertKeys[row.company_id] =
                    (this.state.revertKeys[row.company_id] || 0) + 1;
                this.notification.add(
                    _t(
                        "The field '%s' is required and cannot be empty. The previous value has been restored.",
                        this.props.fieldString,
                    ),
                    { type: "warning" },
                );
            }
        }
    }

    /**
     * Guarda la selección de una opción (llamado desde onSelect de cada opción de sources).
     */
    onSelectValue(row, option) {
        this.state.changes[row.company_id] = {
            value_id: option.value,
            display_value: option.label,
            is_reset: false,
        };
    }

    /**
     * Callback cuando el usuario borra el texto del autocomplete (vaciar explícito).
     * Guarda ``false`` en el JSON → campo vacío pero específico.
     */
    onClearValue(row) {
        this.state.changes[row.company_id] = {
            value_id: false,
            display_value: null,
            is_reset: false,
        };
    }

    /**
     * Resetea la clave del JSON para esta compañía → vuelve al fallback global.
     * Distingue de «vaciar»: aquí se ELIMINA la clave del JSON.
     */
    onResetRow(row) {
        this.state.changes[row.company_id] = { is_reset: true };
    }

    /**
     * Maneja cambios en campos de tipo selection.
     */
    onSelectionChange(row, ev) {
        const rawValue = ev.target.value;
        let value;
        let option;

        if (rawValue === "__false__" || rawValue === "") {
            // Empty sentinel or explicit false — always boolean false
            value = false;
            option = this.state.selectionOptions.find(([k]) => k === false);
        } else {
            // DOM value is always a string; find the option whose key, cast to
            // string, matches — then use the original typed key to preserve the type.
            option = this.state.selectionOptions.find(([k]) => String(k) === rawValue);
            value = option ? option[0] : rawValue;
        }

        const display_value = option ? String(option[1]) : (value ? String(value) : "");
        this.state.changes[row.company_id] = {
            value_id: value,
            display_value,
            is_reset: false,
        };
    }

    /**
     * Maneja cambios en campos de tipo boolean (checkbox / toggle).
     */
    onBooleanChange(row, ev) {
        const value = ev.target.checked;
        this.state.changes[row.company_id] = {
            value_id: value,
            display_value: String(value),
            is_reset: false,
        };
    }

    /**
     * Maneja cambios en campos de tipo char / text / integer / float / date.
     */
    onScalarChange(row, ev) {
        let value = ev.target.value;
        if (this.state.fieldType === "integer") {
            value = value !== "" ? parseInt(value, 10) : false;
        } else if (this.state.fieldType === "float") {
            value = value !== "" ? parseFloat(value) : false;
        } else if (value === "") {
            value = false;
        }
        this.state.changes[row.company_id] = {
            value_id: value,
            display_value: String(ev.target.value),
            is_reset: false,
        };
    }

    /**
     * Propagates the current effective value of a parent row to all its
     * descendants by writing into state.changes (pending, not yet saved).
     * This ensures that clicking Discard rolls back the copy just like any
     * other unsaved edit.
     */
    onCopyToChildren(row) {
        const effective = this._getEffectiveRow(row);
        this._applyToDescendants(row, effective.value_id, effective.display_value);
    }

    /**
     * Recursively fills state.changes for all descendants of `row`.
     */
    _applyToDescendants(row, value_id, display_value) {
        const children = this.state.rows.filter((r) => r.parent_id === row.company_id);
        for (const child of children) {
            this.state.changes[child.company_id] = { value_id, display_value, is_reset: false };
            this._applyToDescendants(child, value_id, display_value);
        }
    }

    // ---------------------------------------------------------------
    // Guardar / Descartar
    // ---------------------------------------------------------------

    /**
     * Lógica interna de guardado. Retorna true si tuvo éxito.
     */
    async _saveChanges() {
        if (!Object.keys(this.state.changes).length) return { saved: [], skipped: [] };

        const valuesDict = {};
        for (const row of this.state.rows) {
            const change = this.state.changes[row.company_id];
            if (!change) continue;
            if (change.is_reset) {
                valuesDict[String(row.company_id)] = "RESET";
            } else {
                const effective = this._getEffectiveRow(row);
                if (!effective.is_specific) continue;
                valuesDict[String(row.company_id)] = effective.value_id ?? false;
            }
        }

        const result = await this.orm.call(
            "base.company.dependent",
            "set_company_dependent_values",
            [this.props.resModel, this.props.resId, this.props.fieldName, valuesDict],
        );

        this.cdService.invalidate(this.props.resModel, this.props.resId);
        return result;
    }

    async onSave() {
        const result = await this._saveChanges();
        const skipped = result.skipped || [];

        if (skipped.length) {
            // Some companies could not be saved due to company crossover.
            // Reload the dialog so it reflects what was actually persisted,
            // and show a sticky warning listing the incompatible companies.
            await this._loadValues();
            this.state.changes = {};
            this.state.revertKeys = {};

            const skippedNames = skipped.map((s) => s.name).join(", ");
            this.notification.add(
                _t(
                    "Saved %s company value(s). Could not save %s due to company inconsistencies: %s.",
                    result.saved.length,
                    skipped.length,
                    skippedNames,
                ),
                { type: "warning", sticky: true },
            );
            // Keep the dialog open so the user can see what remains
            return;
        }

        this.notification.add(
            _t("Values saved successfully."),
            { type: "success" },
        );

        await this.props.onSaved();
        this.props.close();
    }
}

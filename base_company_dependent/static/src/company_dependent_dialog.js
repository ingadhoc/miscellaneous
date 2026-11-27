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
 * Maneja uno o varios campos a la vez: un campo de formulario abre el diálogo
 * con el suyo, y un bloque de Ajustes lo abre con todos los que varían por
 * compañía, que se muestran como una columna cada uno.
 *
 * Análogo a TranslationDialog del módulo ``web``.
 */
export class CompanyDependentDialog extends Component {
    static template = "base_company_dependent.CompanyDependentDialog";
    static components = { Dialog, AutoComplete };
    static props = {
        // Un solo campo (campo de formulario). Alternativa a `fields`.
        fieldName: { type: String, optional: true },
        fieldString: { type: String },
        // Varios campos (bloque de Ajustes), en orden de vista.
        fields: { type: Array, element: Object, optional: true },
        required: { type: Boolean },
        resId: { type: Number },
        resModel: { type: String },
        onSaved: { type: Function },
        close: { type: Function },
        mode: { validate: (v) => v === null || v === "json" || v === "orm", optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.cdService = useService("company_dependent");
        this.notification = useService("notification");

        this.title = _t("Company Values: %s", this.props.fieldString);

        this.state = useState({
            /** Metadata por campo, en el orden pedido. */
            fields: [],
            /** Una fila por compañía; cada una con `values[fieldName]`. */
            rows: [],
            /** Cambios pendientes: changes[fieldName][company_id] = {value_id, is_reset} */
            changes: {},
            /** Counter per field+row to force AutoComplete re-render on revert */
            revertKeys: {},
        });

        onWillStart(() => this._loadValues());
    }

    /**
     * Los campos pedidos, normalizados: el llamador de un solo campo pasa
     * `fieldName`, el de un bloque pasa `fields`.
     */
    get fieldDefs() {
        if (this.props.fields && this.props.fields.length) {
            return this.props.fields;
        }
        return [{ field_name: this.props.fieldName, field_string: this.props.fieldString }];
    }

    /**
     * Con un solo campo la tabla conserva las columnas Valor / Estado /
     * Acciones; con varios, cada campo es su propia columna y el estado y el
     * reset viven adentro de su celda.
     */
    get isSingleField() {
        // Estrictamente uno: con cero (el diálogo todavía no cargó, o el
        // servidor no devolvió ninguno) la rama de un campo leería
        // `state.fields[0]` y reventaría.
        return this.state.fields.length === 1;
    }

    // ---------------------------------------------------------------
    // Textos (getters para evitar problemas del tokenizador OWL con
    // caracteres especiales en expresiones de template)
    // ---------------------------------------------------------------

    get autoCompletePlaceholder() {
        return _t("No value (explicitly False)");
    }

    /**
     * Placeholder por celda: muestra el texto de "vaciar explícitamente" únicamente
     * cuando la celda no tiene ningún valor (ni específico ni fallback). Si tiene
     * un valor por defecto visible, el placeholder queda vacío para no solaparse.
     */
    getRowPlaceholder(field, row) {
        const effective = this._getEffectiveRow(field, row);
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

    /** True cuando alguna columna admite reset: la nota al pie lo explica. */
    get anyCanReset() {
        return this.state.fields.some((field) => field.can_reset !== false);
    }

    // ---------------------------------------------------------------
    // Carga de datos
    // ---------------------------------------------------------------

    async _loadValues() {
        const { resModel, resId, mode } = this.props;
        const fieldNames = this.fieldDefs.map((f) => f.field_name);
        const result = await this.orm.call(
            "base.company.dependent",
            "get_company_dependent_values_multi",
            [resModel, resId, fieldNames],
            { mode: mode || null },
        );
        this.state.fields = result.fields;
        this.state.rows = result.rows.map((row) => ({ ...row }));
    }

    // ---------------------------------------------------------------
    // Helpers de jerarquía
    // ---------------------------------------------------------------

    /**
     * Construye el árbol ordenado para renderizar en el template.
     * Devuelve una lista plana donde cada elemento tiene {row, depth}
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
    // Estado derivado por celda (campo + compañía)
    // ---------------------------------------------------------------

    /** Los datos que el backend trajo para ese campo en esa compañía. */
    _cellData(field, row) {
        return (row.values && row.values[field.field_name]) || {};
    }

    _getChange(field, row) {
        const byCompany = this.state.changes[field.field_name];
        return byCompany ? byCompany[row.company_id] : undefined;
    }

    /**
     * Anota un cambio pendiente. Reemplaza el objeto del campo entero para que
     * OWL vea la mutación aunque la clave todavía no existiera.
     */
    _setChange(field, row, change) {
        this.state.changes[field.field_name] = {
            ...(this.state.changes[field.field_name] || {}),
            [row.company_id]: change,
        };
    }

    _clearChange(field, row) {
        const byCompany = { ...(this.state.changes[field.field_name] || {}) };
        delete byCompany[row.company_id];
        this.state.changes[field.field_name] = byCompany;
    }

    /**
     * Devuelve el estado efectivo de una celda, combinando el original con
     * los cambios pendientes.
     */
    _getEffectiveRow(field, row) {
        const base = this._cellData(field, row);
        const change = this._getChange(field, row);
        if (!change) return base;
        if (change.is_reset) {
            return {
                ...base,
                is_specific: false,
                value_id: base.fallback_value_id ?? null,
                display_value: base.fallback_display_value ?? null,
            };
        }
        return {
            ...base,
            is_specific: true,
            value_id: change.value_id,
            display_value: change.display_value,
        };
    }

    isSpecificRow(field, row) {
        return Boolean(this._getEffectiveRow(field, row).is_specific);
    }

    getDisplayValue(field, row) {
        return this._getEffectiveRow(field, row).display_value || "";
    }

    /** Clase de la fila: solo con un campo la fila entera es específica o no. */
    getRowClass(row, depth) {
        const base = `o_cd_row o_cd_depth_${depth}`;
        if (!this.isSingleField) return base;
        const field = this.state.fields[0];
        return `${base} ${this.isSpecificRow(field, row) ? "o_cd_row_specific" : "o_cd_row_default"}`;
    }

    /**
     * Un campo requerido no se puede vaciar. El dato viene del campo del
     * formulario que abrió el diálogo, así que solo aplica con un campo: en un
     * bloque de Ajustes no sabemos cuál de las columnas lo es.
     */
    isRequiredField() {
        return this.isSingleField && this.props.required;
    }

    // ---------------------------------------------------------------
    // Interacción del usuario
    // ---------------------------------------------------------------

    /**
     * Returns a unique key for the AutoComplete component of a given cell.
     * Incrementing this key forces OWL to destroy and re-create the component,
     * which is needed when reverting changes on required fields so the input
     * text goes back to the effective display value.
     */
    getAutoCompleteKey(field, row) {
        const key = `${field.field_name}-${row.company_id}`;
        return `ac-${key}-${this.state.revertKeys[key] || 0}`;
    }

    /**
     * Genera las sources para el componente AutoComplete de una celda.
     *
     * El domain pasado a name_search combina:
     *   - El domain estático del campo original (ej. filtro por tipo de cuenta).
     *   - El domain de compañía: comodel._check_company_domain(company).
     * Ambos vienen pre-calculados desde el backend en la celda.
     *
     * IMPORTANTE: en la API de AutoComplete el callback de selección va en cada
     * opción como `onSelect()`, NO como prop del componente.
     */
    getAutoCompleteSources(field, row) {
        const self = this;
        // Usamos el domain efectivo calculado por el backend para esta celda.
        // Fallback a [] si no lo trae (p.ej. campos no-many2one).
        const effectiveDomain = this._cellData(field, row).domain || [];
        const comodelName = field.comodel_name;
        return [
            {
                options: async (search) => {
                    if (!comodelName) return [];
                    const results = await self.orm.call(
                        comodelName,
                        "name_search",
                        [],
                        { name: search, domain: effectiveDomain, limit: 10 },
                    );
                    return results.map(([id, label]) => ({
                        value: id,
                        label,
                        onSelect: () => self.onSelectValue(field, row, { value: id, label }),
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
    onAutoCompleteChange(field, row, info) {
        if (!info.inputValue && !info.isOptionSelected) {
            if (!this.isRequiredField()) {
                this.onClearValue(field, row);
            } else {
                // Campo required: no se puede vaciar. Revertimos cualquier cambio
                // pendiente para esta celda y notificamos al usuario.
                this._clearChange(field, row);
                // Bump the revert key to force AutoComplete to re-render with the
                // original (or fallback) display value.
                const key = `${field.field_name}-${row.company_id}`;
                this.state.revertKeys[key] = (this.state.revertKeys[key] || 0) + 1;
                this.notification.add(
                    _t(
                        "The field '%s' is required and cannot be empty. The previous value has been restored.",
                        field.field_string,
                    ),
                    { type: "warning" },
                );
            }
        }
    }

    /**
     * Guarda la selección de una opción (llamado desde onSelect de cada opción de sources).
     */
    onSelectValue(field, row, option) {
        this._setChange(field, row, {
            value_id: option.value,
            display_value: option.label,
            is_reset: false,
        });
    }

    /**
     * Callback cuando el usuario borra el texto del autocomplete (vaciar explícito).
     * Guarda ``false`` en el JSON → campo vacío pero específico.
     */
    onClearValue(field, row) {
        this._setChange(field, row, {
            value_id: false,
            display_value: null,
            is_reset: false,
        });
    }

    /**
     * Resetea la clave del JSON para esta compañía → vuelve al fallback global.
     * Distingue de «vaciar»: aquí se ELIMINA la clave del JSON.
     */
    onResetRow(field, row) {
        this._setChange(field, row, { is_reset: true });
    }

    /**
     * Maneja cambios en campos de tipo selection.
     */
    onSelectionChange(field, row, ev) {
        const rawValue = ev.target.value;
        const options = field.selection_options || [];
        let value;
        let option;

        if (rawValue === "__false__" || rawValue === "") {
            // Empty sentinel or explicit false — always boolean false
            value = false;
            option = options.find(([k]) => k === false);
        } else {
            // DOM value is always a string; find the option whose key, cast to
            // string, matches — then use the original typed key to preserve the type.
            option = options.find(([k]) => String(k) === rawValue);
            value = option ? option[0] : rawValue;
        }

        const display_value = option ? String(option[1]) : (value ? String(value) : "");
        this._setChange(field, row, { value_id: value, display_value, is_reset: false });
    }

    /**
     * Maneja cambios en campos de tipo boolean (checkbox / toggle).
     */
    onBooleanChange(field, row, ev) {
        const value = ev.target.checked;
        this._setChange(field, row, {
            value_id: value,
            display_value: String(value),
            is_reset: false,
        });
    }

    /**
     * Maneja cambios en campos de tipo char / text / integer / float / date.
     */
    onScalarChange(field, row, ev) {
        let value = ev.target.value;
        if (field.field_type === "integer") {
            value = value !== "" ? parseInt(value, 10) : false;
        } else if (field.field_type === "float") {
            value = value !== "" ? parseFloat(value) : false;
        } else if (value === "") {
            value = false;
        }
        this._setChange(field, row, {
            value_id: value,
            display_value: String(ev.target.value),
            is_reset: false,
        });
    }

    /**
     * Propagates the current effective values of a parent row to all its
     * descendants by writing into state.changes (pending, not yet saved).
     * This ensures that clicking Discard rolls back the copy just like any
     * other unsaved edit. Con varias columnas copia el bloque entero, que es
     * lo que el botón promete en esa fila.
     */
    onCopyToChildren(row) {
        for (const field of this.state.fields) {
            const effective = this._getEffectiveRow(field, row);
            this._applyToDescendants(field, row, effective.value_id, effective.display_value);
        }
    }

    /**
     * Recursively fills state.changes for all descendants of `row`.
     */
    _applyToDescendants(field, row, value_id, display_value) {
        const children = this.state.rows.filter((r) => r.parent_id === row.company_id);
        for (const child of children) {
            this._setChange(field, child, { value_id, display_value, is_reset: false });
            this._applyToDescendants(field, child, value_id, display_value);
        }
    }

    // ---------------------------------------------------------------
    // Guardar / Descartar
    // ---------------------------------------------------------------

    /**
     * Lógica interna de guardado. Devuelve los saved/skipped de todas las
     * columnas juntos: al usuario le importa qué compañía no se pudo guardar,
     * no en qué columna estaba.
     */
    async _saveChanges() {
        const valuesByField = {};
        for (const field of this.state.fields) {
            const valuesDict = {};
            for (const row of this.state.rows) {
                const change = this._getChange(field, row);
                if (!change) continue;
                if (change.is_reset) {
                    valuesDict[String(row.company_id)] = "RESET";
                } else {
                    const effective = this._getEffectiveRow(field, row);
                    if (!effective.is_specific) continue;
                    valuesDict[String(row.company_id)] = effective.value_id ?? false;
                }
            }
            if (Object.keys(valuesDict).length) {
                valuesByField[field.field_name] = valuesDict;
            }
        }

        if (!Object.keys(valuesByField).length) return { saved: [], skipped: [] };

        const result = await this.orm.call(
            "base.company.dependent",
            "set_company_dependent_values_multi",
            [this.props.resModel, this.props.resId, valuesByField],
            { mode: this.props.mode || null },
        );

        const saved = [];
        const skipped = [];
        for (const perField of Object.values(result)) {
            saved.push(...(perField.saved || []));
            skipped.push(...(perField.skipped || []));
        }

        this.cdService.invalidate(this.props.resModel, this.props.resId);
        return { saved, skipped };
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

            // La misma compañía puede fallar en más de una columna.
            const skippedNames = [...new Set(skipped.map((s) => s.name))].join(", ");
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

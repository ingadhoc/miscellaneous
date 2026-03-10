/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Diálogo de gestión multicompañía para campos company_dependent.
 *
 * Carga los valores por compañía desde el backend y permite:
 *   - Ver si cada compañía tiene un valor «Específico» o «Por Defecto».
 *   - Editar el valor (Many2One con autocompletado).
 *   - Vaciar explícitamente el campo (guarda ``false`` en el JSON).
 *   - Resetear la clave del JSON (restaura al fallback global).
 *
 * Análogo a TranslationDialog del módulo ``web``.
 */
export class CompanyDependentDialog extends Component {
    static template = "base_company_dependant.CompanyDependentDialog";
    static components = { Dialog, AutoComplete };
    static props = {
        fieldName: { type: String },
        resId: { type: Number },
        resModel: { type: String },
        onSaved: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.cdService = useService("company_dependent");
        this.notification = useService("notification");

        this.title = _t("Valores por compañía: %s", this.props.fieldName);

        this.state = useState({
            rows: [],           // [{company_id, company_name, is_specific, value_id, display_value}]
            fieldType: null,
            comodelName: null,
            /** Cambios pendientes: Map<company_id, {value_id, is_reset}> */
            changes: {},
        });

        onWillStart(() => this._loadValues());
    }

    // ---------------------------------------------------------------
    // Textos (getters para evitar problemas del tokenizador OWL con
    // caracteres especiales en expresiones de template)
    // ---------------------------------------------------------------

    get autoCompletePlaceholder() {
        return _t("Sin valor (vaciar explicitamente)");
    }

    get resetButtonTitle() {
        return _t("Restaurar al valor por defecto (elimina la clave del JSON)");
    }

    get labelSpecific() {
        return _t("Especifico");
    }

    get labelDefault() {
        return _t("Por Defecto");
    }

    get loadingText() {
        return _t("Cargando valores por compania...");
    }

    get footerNoteHtml() {
        // Devuelve partes separadas para el template (evita innerHTML crudo)
        return {
            vaciar: _t("Vaciar"),
            vaciarDesc: _t("guarda un valor vacio explicito (badge Especifico)."),
            reset: _t("Reset"),
            resetDesc: _t("elimina la clave del JSON y restaura el valor por defecto global."),
        };
    }

    // ---------------------------------------------------------------
    // Carga de datos
    // ---------------------------------------------------------------

    async _loadValues() {
        const { resModel, resId, fieldName } = this.props;
        const result = await this.orm.call(
            "base.company.dependant",
            "get_company_dependent_values",
            [resModel, resId, fieldName],
        );
        this.state.rows = result.values.map((row) => ({ ...row }));
        this.state.fieldType = result.field_type;
        this.state.comodelName = result.comodel_name;
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
            return { ...row, is_specific: false, value_id: null, display_value: null };
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
            this.onClearValue(row);
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

    // ---------------------------------------------------------------
    // Guardar / Descartar
    // ---------------------------------------------------------------

    async onSave() {
        if (!Object.keys(this.state.changes).length) {
            this.props.close();
            return;
        }

        // Construir el dict que espera set_company_dependent_values.
        // { str(company_id): value_id | false | "RESET" }
        const valuesDict = {};
        for (const [companyId, change] of Object.entries(this.state.changes)) {
            if (change.is_reset) {
                valuesDict[String(companyId)] = "RESET";
            } else {
                valuesDict[String(companyId)] = change.value_id ?? false;
            }
        }

        await this.orm.call(
            "base.company.dependant",
            "set_company_dependent_values",
            [this.props.resModel, this.props.resId, this.props.fieldName, valuesDict],
        );

        // Invalida la caché del servicio para que el formulario refresque isSpecific.
        this.cdService.invalidate(this.props.resModel, this.props.resId);

        this.notification.add(
            _t("Valores guardados correctamente."),
            { type: "success" },
        );

        await this.props.onSaved();
        this.props.close();
    }
}

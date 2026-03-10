/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { CompanyDependentDialog } from "./company_dependent_dialog";

/**
 * Botón de ícono fa-building-o que se muestra junto a campos Many2one
 * que tienen company_dependent === true.
 *
 * El estado ``isSpecific`` lo gestiona el Many2OneField padre a través del
 * servicio ``company_dependent``, y lo pasa como prop.
 *
 * Props:
 *   - fieldName  {string}       : nombre técnico del campo.
 *   - record     {Record}       : instancia del record del formulario.
 *   - isSpecific {boolean|null} : null = cargando, true = específico, false = fallback.
 *   - onSaved    {Function}     : callback llamado tras guardar en el diálogo
 *                                 (el padre recarga el record y refresca cdState).
 */
export class CompanyDependentButton extends Component {
    static template = "base_company_dependant.CompanyDependentButton";
    static props = {
        fieldName: { type: String },
        record: { type: Object },
        isSpecific: { validate: (v) => v === null || typeof v === "boolean" },
        onSaved: { type: Function, optional: true },
    };

    setup() {
        this.addDialog = useOwnedDialogs();
    }

    get title() {
        if (this.props.isSpecific === null) {
            return _t("Cargando información de compañías…");
        }
        return this.props.isSpecific
            ? _t("Valor específico para esta compañía. Clic para gestionar.")
            : _t("Valor por defecto (fallback). Clic para gestionar.");
    }

    async onClick() {
        // Guardar el registro antes de abrir el diálogo (igual que las traducciones).
        const saved = await this.props.record.save();
        if (!saved) {
            return;
        }
        const { resModel, resId } = this.props.record;
        this.addDialog(CompanyDependentDialog, {
            fieldName: this.props.fieldName,
            resId,
            resModel,
            onSaved: async () => {
                await this.props.record.load();
                if (this.props.onSaved) {
                    await this.props.onSaved();
                }
            },
        });
    }
}

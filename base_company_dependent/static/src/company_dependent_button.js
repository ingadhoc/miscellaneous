/** @odoo-module **/

import { Component, types, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { CompanyDependentDialog } from "./company_dependent_dialog";

/**
 * Botón de ícono business que se muestra junto a campos Many2one
 * que tienen company_dependent === true.
 *
 * El estado ``isSpecific`` lo gestiona el Many2OneField padre a través del
 * servicio ``company_dependent``, y lo pasa como prop.
 *
 * Props:
 *   - fieldName  {string}       : nombre técnico del campo.
 *   - record     {Record}       : instancia del record del formulario.
 *   - isSpecific {boolean|null|undefined} : null = cargando, true = específico,
 *                                 false = fallback, undefined = no aplica (ajustes).
 *   - onSaved    {Function}     : callback llamado tras guardar en el diálogo
 *                                 (el padre recarga el record y refresca cdState).
 */
export class CompanyDependentButton extends Component {
    static template = "base_company_dependent.CompanyDependentButton";
<<<<<<< 208b26e0e55785923fe13f62205ef33006ebee79
    props = useProps({
        fieldName: types.string(),
        fieldString: types.string(),
        required: types.boolean(),
        record: types.object(),
        isSpecific: types.or([types.literal(null), types.boolean()]),
        onSaved: types.function().optional(),
    });
||||||| 01ef66dbf3ec84f203e9b3c63c47739c308d4150
    static props = {
        fieldName: { type: String },
        fieldString: { type: String },
        required: { type: Boolean },
        record: { type: Object },
        isSpecific: { validate: (v) => v === null || typeof v === "boolean" },
        onSaved: { type: Function, optional: true },
    };
=======
    static props = {
        fieldName: { type: String, optional: true },
        fieldString: { type: String },
        required: { type: Boolean },
        record: { type: Object },
        // Left undefined where no specific/default state applies (settings).
        isSpecific: { validate: (v) => v === null || typeof v === "boolean", optional: true },
        onSaved: { type: Function, optional: true },
        mode: { validate: (v) => v == null || typeof v === "string", optional: true },
    };
>>>>>>> 2f7d49b093ce9012e8d29e591ffb369db801f4d9

    setup() {
        this.addDialog = useOwnedDialogs();
        this.notification = useService("notification");
    }

    get title() {
        if (this.props.isSpecific === undefined) {
            return _t("Values set here are company-specific. Click to manage.");
        }
        if (this.props.isSpecific === null) {
            return _t("Loading company information…");
        }
        return this.props.isSpecific
            ? _t("Specific value for this company. Click to manage.")
            : _t("Default value (fallback). Click to manage.");
    }

    async onClick() {
        if (!this.props.fieldName) {
            this.notification.add(
                _t("These values are company-specific. Switch company to see or edit values for other companies."),
                { type: "info" },
            );
            return;
        }
        // Cerrar cualquier AutoComplete/dropdown abierto en el formulario antes
        // de guardar, para evitar que el dropdown del campo aparezca detrás del diálogo.
        if (document.activeElement && document.activeElement !== document.body) {
            document.activeElement.blur();
        }
        // Guardar el registro antes de abrir el diálogo (igual que las traducciones).
        const saved = await this.props.record.save();
        if (!saved) {
            return;
        }
        const { resModel, resId } = this.props.record;
        this.addDialog(CompanyDependentDialog, {
            fieldName: this.props.fieldName,
            fieldString: this.props.fieldString,
            required: this.props.required,
            resId,
            resModel,
            mode: this.props.mode || null,
            onSaved: async () => {
                await this.props.record.load();
                if (this.props.onSaved) {
                    await this.props.onSaved();
                }
            },
        });
    }
}

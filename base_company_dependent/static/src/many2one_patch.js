/** @odoo-module **/
/**
 * Patch sobre Many2OneField para campos company_dependent.
 *
 * Cuando el campo tiene `company_dependent: true` en la definición del modelo:
 *   1. Inyecta el ícono fa-building-o a la derecha del input.
 *   2. Aplica la clase CSS ``o_cd_fallback`` al wrapper cuando el valor proviene
 *      del fallback global (clave del company_id actual ausente en el JSON).
 *
 * El estado ``isSpecific`` se obtiene del servicio ``company_dependent``, que
 * hace UNA sola query SQL por formulario para todos los campos company_dependent
 * del modelo.
 */

import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { CompanyDependentButton } from "./company_dependent_button";
import { patch } from "@web/core/utils/patch";
import { useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// ──────────────────────────────────────────────────────────────────────────────
// Patch del componente Many2OneField
// ──────────────────────────────────────────────────────────────────────────────
patch(Many2OneField.prototype, {
    setup() {
        super.setup();

        // Llamamos a useService/useState siempre (sin condicional) para respetar
        // el orden de los hooks de OWL, aunque el servicio solo se usa cuando
        // isCompanyDependent === true.
        this._cdService = useService("company_dependent");
        this._cdState = useState({ isSpecific: null });

        if (this.isCompanyDependent) {
            // Carga inicial: NO invalidar para aprovechar el batching del servicio.
            // Si hay 5 campos company_dependent en el form, todos comparten la misma
            // Promise y se hace UNA sola query SQL.
            onWillStart(() => this._loadCDMeta());
        }
    },

    /**
     * Verdadero si el campo está marcado como company_dependent en el modelo.
     */
    get isCompanyDependent() {
        return (
            this.props.record?.fields?.[this.props.name]?.company_dependent === true
        );
    },

    /**
     * Carga el isSpecific desde el servicio (usa caché, no invalida).
     * Se usa tanto para la carga inicial como para el refresh post-guardado
     * (en ese caso el diálogo ya invalidó la caché antes de llamar a este método).
     */
    async _loadCDMeta() {
        const { resModel, resId } = this.props.record;
        if (!resId) return;
        const meta = await this._cdService.getMetaForRecord(resModel, resId);
        this._cdState.isSpecific = meta[this.props.name] ?? false;
    },
});

// Registramos el sub-componente CompanyDependentButton en la lista de componentes
// de Many2OneField sin reemplazar la lista entera.
Many2OneField.components = {
    ...Many2OneField.components,
    CompanyDependentButton,
};

// Reemplazamos el template por el nuestro extendido.
Many2OneField.template = "base_company_dependent.Many2OneField";

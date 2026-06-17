import { _t } from "@web/core/l10n/translation";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class FirstStepsGuide extends Component {
    static template = "base_import_ux.FirstStepsGuide";
    static components = { ControlPanel };
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.env.config.setDisplayName(_t("First Steps"));

        // Each card is shown depending on whether the module it needs is
        // installed. Same pattern as the Enterprise accounting guide (t-if +
        // searchRead on ir.module.module). Avoids bridge modules: a single
        // module serves every combination of installed modules.
        this.state = useState({
            hasProduct: false,
            hasStock: false,
            hasAccountImport: false,
        });

        onWillStart(async () => {
            const modules = await this.orm.searchRead(
                "ir.module.module",
                [
                    ["name", "in", ["product", "stock", "account_balance_import"]],
                    ["state", "=", "installed"],
                ],
                ["name"]
            );
            const installed = modules.map((m) => m.name);
            this.state.hasProduct = installed.includes("product");
            this.state.hasStock = installed.includes("stock");
            this.state.hasAccountImport = installed.includes("account_balance_import");
        });
    }

    // Open an action by XML id. For actions belonging to optional modules (e.g.
    // accounting) the xmlid is passed as a string: it is resolved only on click,
    // so it does not create an install dependency.
    openAction(xmlId) {
        this.actionService.doAction(xmlId);
    }
}

registry.category("actions").add("first_steps_guide", FirstStepsGuide);

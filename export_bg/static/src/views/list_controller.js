/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {
    async downloadExport(fields, import_compat, format) {
        const resIds = this.isDomainSelected ? false : await this.getSelectedResIds();
        const recordCount = resIds ? resIds.length : (this.model.root.count || 0);

        const threshold = await this.model.orm.call(
            "ir.model",
            "get_export_threshold",
            []
        );

        if (recordCount > threshold) {
            const data = {
                model: this.props.resModel,
                fields: fields,
                ids: resIds,
                domain: this.model.root.domain,
                import_compat: import_compat,
            };

            const actionResult = await this.model.orm.call(
                "ir.model",
                "web_export",
                [],
                {
                    data: JSON.stringify(data),
                    export_format: format,
                }
            );

            if (actionResult && actionResult.type === "ir.actions.client") {
                this.env.services.action.doAction(actionResult);
            }
        } else {
            await super.downloadExport(...arguments);
        }
    },
});

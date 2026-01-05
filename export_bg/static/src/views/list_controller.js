/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

patch(ListController.prototype, {
    async downloadExport(fields, import_compat, format) {
        const resIds = this.isDomainSelected ? false : await this.getSelectedResIds();
        const recordCount = resIds ? resIds.length : (this.model.root.count || 0);

        const threshold = await this.model.orm.call(
            "ir.config_parameter",
            "get_param",
            ["export_bg.record_threshold", "500"]
        );

        if (recordCount > parseInt(threshold)) {
            const data = {
                model: this.props.resModel,
                fields: fields,
                ids: resIds,
                domain: this.model.root.domain,
                import_compat: import_compat,
            };

            const method = format === "csv" ? "web_export_csv" : "web_export_xlsx";
            const actionResult = await this.model.orm.call(
                "ir.model",
                "bg_enqueue",
                [method],
                {
                    data: JSON.stringify(data),
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

/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";

patch(ExportDataDialog.prototype, {
    async onClickExportButton() {
        if (!this.state.exportList.length) {
            return super.onClickExportButton();
        }

        const root = this.props.root;
        const recordCount = !root.isDomainSelected && root.selection.length > 0
            ? root.selection.length
            : root.count || 0;

        const threshold = await this.orm.call(
            "ir.model",
            "get_export_threshold",
            []
        );

        if (recordCount > threshold) {
            const format = this.availableFormats[this.state.selectedFormat].tag;
            const method = format === "csv" ? "web_export_csv" : "web_export_xlsx";

            const exportedFields = this.state.exportList.map((field) => ({
                string: field.label || field.string,
                value: field.name || field.id,
            }));

            const data = {
                model: root.resModel,
                fields: exportedFields,
                ids: !root.isDomainSelected && root.selection.length > 0
                    ? root.selection.map((e) => e.resId)
                    : false,
                domain: root.domain,
                context: root.context,
                import_compat: this.isCompatible,
            };

            this.state.disabled = true;
            const result = await this.orm.call(
                "ir.model",
                "web_export",
                [],
                {
                    data: JSON.stringify(data),
                    export_format: format,
                }
            );
            this.state.disabled = false;

<<<<<<< d8b2a1b32f8d5f7b53e6b057021cbbe0721e83ed
            const actionResult = result[0];
            if (actionResult && actionResult.type) {
                this.env.services.action.doAction(actionResult);
||||||| ded14565e127b647e6546ecdb3b750b0ad07c467
            if (actionResult && actionResult.type === "ir.actions.client") {
                this.env.services.action.doAction(actionResult);
=======
            if (actionResult && actionResult[0].type === "ir.actions.client") {
                this.env.services.action.doAction(actionResult[0]);
>>>>>>> 9f5f4ba998c3e2951570b8a03c138892cbda5b09
            }
        } else {
            await super.onClickExportButton();
        }
    },
});

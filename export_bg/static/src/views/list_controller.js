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

            const actionResult = result[0];
            if (actionResult && actionResult.type) {
                this.env.services.action.doAction(actionResult);
            }
        } else {
            await super.onClickExportButton();
        }
    },
});

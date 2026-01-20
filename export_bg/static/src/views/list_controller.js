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

<<<<<<< e792703361b22545f4f8e17c9c86deca306c7b8d
            this.state.disabled = true;
            const result = await this.orm.call(
||||||| 5506347fdcde5c846885d14f231efa51aa8b2bae
            const method = format === "csv" ? "web_export_csv" : "web_export_xlsx";
            const actionResult = await this.model.orm.call(
=======
            const actionResult = await this.model.orm.call(
>>>>>>> 53e4d3ace0697389252819e21e08e2fd9c5fd8f2
                "ir.model",
<<<<<<< e792703361b22545f4f8e17c9c86deca306c7b8d
                "bg_enqueue",
                [method],
                { data: JSON.stringify(data) }
||||||| 5506347fdcde5c846885d14f231efa51aa8b2bae
                "bg_enqueue",
                [method],
                {
                    data: JSON.stringify(data),
                }
=======
                "web_export",
                [],
                {
                    data: JSON.stringify(data),
                    export_format: format,
                }
>>>>>>> 53e4d3ace0697389252819e21e08e2fd9c5fd8f2
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

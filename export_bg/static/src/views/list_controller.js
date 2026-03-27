/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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
                name: field.name || field.id,
                label: field.label || field.string,
                store: field.store,
                type: field.field_type || field.type,
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
                groupby: root.groupBy,
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

            return { closeWizard: true };
        } else {
            await super.onClickExportButton();
        }
    },

    async onExportData() {
        let closeDialog;
        const dialogProps = {
            context: this.props.context,
            defaultExportList: this.defaultExportList,
            download: async (...args) => {
                const result = await this.downloadExport(...args);
                if (result && result.closeWizard && closeDialog) {
                    closeDialog();
                }
                return result;
            },
            getExportedFields: this.getExportedFields.bind(this),
            root: this.model.root,
        };
        closeDialog = this.dialogService.add(ExportDataDialog, dialogProps);
    },
});

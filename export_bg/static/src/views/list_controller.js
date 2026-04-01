/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";

patch(ListController.prototype, {
    async downloadExport(fields, import_compat, format) {
        const resIds = this.isDomainSelected ? false : await this.getSelectedResIds();
        const recordCount = resIds ? resIds.length : (this.model.root.count || 0);
        const exportedFields = fields.map((field) => ({
            name: field.name || field.id,
            value: field.name || field.id,
            label: field.label || field.string,
            string: field.label || field.string,
            store: field.store,
            type: field.field_type || field.type,
        }));

        if (import_compat) {
            exportedFields.unshift({
                name: "id",
                label: _t("External ID"),
            });
        }

        const threshold = await this.model.orm.call(
            "ir.model",
            "get_export_threshold",
            []
        );

        if (recordCount > threshold) {
            const data = {
                model: this.props.resModel,
                fields: exportedFields,
                ids: resIds,
                domain: this.model.root.domain,
                import_compat: import_compat,
                groupby: this.model.root.groupBy,
                context: this.props.context,
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

            if (Array.isArray(actionResult) && actionResult[0]?.type === "ir.actions.client") {
                this.env.services.action.doAction(actionResult[0]);
            }

            return { closeWizard: true };
        } else {
            await super.downloadExport(...arguments);
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

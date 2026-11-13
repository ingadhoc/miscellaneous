from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def get_print_jobs(self, report_name, docids, data) -> list:
        """Add a PrintNode job without rendering the report.

        The report is rendered when printing, as the user, in
        ``printer.printer.printnode_print``: this method also runs from
        ``_read_format`` under the sudo of ``/web/action/load``.
        """
        jobs = super().get_print_jobs(report_name, docids, data)
        report = self._get_report(report_name)
        if not report.printer_ids.filtered(lambda p: p.type == "printnode"):
            return jobs

        if isinstance(docids, models.BaseModel):
            docids = docids.ids
        elif isinstance(docids, int):
            docids = [docids]
        jobs.append(
            {
                "type": "printnode",
                "report_id": report.id,
                "docids": list(docids or []),
                "data": data,
            }
        )
        return jobs

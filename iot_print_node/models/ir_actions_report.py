import base64

from odoo import api, models

PRINTNODE_JOB_TYPES = {
    "qweb-pdf": "pdf",
    "pdf": "pdf",
    "aeroo": "pdf",
    "qweb-text": "txt",
}


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def get_print_jobs(self, report_name, docids, data) -> list:
        jobs = super().get_print_jobs(report_name, docids, data)
        report = self._get_report(report_name)
        if not report.printer_ids.filtered(lambda p: p.type == "printnode"):
            return jobs

        printnode_type = PRINTNODE_JOB_TYPES.get(report.report_type)
        job = {"type": "printnode", "report_type": report.report_type, "printnode_type": printnode_type}
        if printnode_type:
            report_data = self._render(report_name, docids, data)[0]
            if not report_data:
                return jobs
            job["report"] = base64.b64encode(report_data).decode()
        jobs.append(job)
        return jobs

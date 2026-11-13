import base64

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

PRINTNODE_JOB_TYPES = {
    "qweb-pdf": "pdf",
    "pdf": "pdf",
    "aeroo": "pdf",
    "qweb-text": "txt",
}
PRINTNODE_PROTECTED_FIELDS = {"printnode_account_id", "printnode_identifier", "printnode_status"}
SHIPPING_REPORTS = ("stock_delivery.report_shipping_labels", "stock_delivery.report_shipping_docs")


class Printer(models.Model):
    _inherit = "printer.printer"

    type = fields.Selection(selection_add=[("printnode", "PrintNode")], ondelete={"printnode": "cascade"})
    printnode_account_id = fields.Many2one(
        "printnode.account",
        string="PrintNode Account",
        ondelete="cascade",
        index="btree_not_null",
    )
    printnode_identifier = fields.Char("PrintNode Identifier", readonly=True)
    printnode_status = fields.Selection(
        [
            ("disconnected", "Disconnected"),
            ("connected", "Connected"),
        ],
        default="disconnected",
        readonly=True,
    )

    def _check_printnode_fields_access(self, vals_list):
        # printer.printer is writable by every internal user; which PrintNode printer it points to is not
        if self.env.su or self.env.is_system():
            return
        for vals in vals_list:
            changes_type = "type" in vals and (vals["type"] == "printnode" or any(p.type == "printnode" for p in self))
            if PRINTNODE_PROTECTED_FIELDS & vals.keys() or changes_type:
                raise AccessError(self.env._("Only administrators can link a printer to a PrintNode account"))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_printnode_fields_access(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        self._check_printnode_fields_access([vals])
        return super().write(vals)

    def printnode_print(self, job):
        """Render the report of a job built by ``ir.actions.report.get_print_jobs``,
        as the current user, and send it to PrintNode."""
        self.ensure_one()
        if self.type != "printnode" or not self.printnode_account_id:
            raise UserError(self.env._("Must be a PrintNode printer"))
        report = self.env["ir.actions.report"].browse(job["report_id"]).exists()
        if not report or report.id not in self.sudo().report_ids.ids:
            raise UserError(self.env._("The report is not linked to the printer %s", self.name))
        docids = job.get("docids") or []
        if report.report_name in SHIPPING_REPORTS:
            return [
                self._printnode_send(jobtype, content)
                for jobtype, content in self._printnode_chatter_jobs(report, docids)
            ]
        jobtype = PRINTNODE_JOB_TYPES.get(report.report_type)
        if not jobtype:
            raise UserError(self.env._("Jobtype %s not implemented for Print Node", report.report_type))
        content = report._render(report.report_name, docids, data=job.get("data"))[0]
        return self._printnode_send(jobtype, base64.b64encode(content).decode())

    def _printnode_chatter_jobs(self, report, docids):
        """Carrier labels and documents are attachments of the picking: send all of them,
        as delivery_iot did in 19.0, instead of the single PDF that _render returns."""
        attachments = report.get_reports_from_chatter(report.report_name, docids)
        if not attachments:
            raise UserError(
                self.env._(
                    "This action is meant to print %s attachments from the chatter: none was found.",
                    report.name,
                )
            )
        jobs = []
        for attachment in attachments:
            if attachment.mimetype == "application/pdf":
                jobtype = "pdf"
            elif ".zpl" in attachment.name.lower() or (attachment.mimetype or "").startswith("text/"):
                jobtype = "txt"
            else:
                raise UserError(
                    self.env._(
                        "PrintNode can only print PDF or ZPL attachments, and %s is not one of them.",
                        attachment.name,
                    )
                )
            jobs.append((jobtype, base64.b64encode(attachment.raw).decode()))
        return jobs

    def _printnode_send(self, jobtype, content):
        return self.printnode_account_id.sudo()._print_node_submit_job(
            printerid=self.printnode_identifier,
            jobtype=jobtype,
            content=content,
        )

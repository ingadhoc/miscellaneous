import base64

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

PRINTNODE_JOB_TYPES = {
    "qweb-pdf": "pdf",
    "pdf": "pdf",
    "aeroo": "pdf",
    "qweb-text": "txt",
}
PRINTNODE_PROTECTED_FIELDS = {"printnode_account_id", "printnode_identifier"}


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
        if any(PRINTNODE_PROTECTED_FIELDS & vals.keys() for vals in vals_list):
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
        jobtype = PRINTNODE_JOB_TYPES.get(report.report_type)
        if not jobtype:
            raise UserError(self.env._("Jobtype %s not implemented for Print Node", report.report_type))
        content = report._render(report.report_name, job.get("docids") or [], data=job.get("data"))[0]
        return self.printnode_account_id.sudo()._print_node_submit_job(
            printerid=self.printnode_identifier,
            jobtype=jobtype,
            content=base64.b64encode(content).decode(),
        )

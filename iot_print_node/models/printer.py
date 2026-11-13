from odoo import fields, models
from odoo.exceptions import UserError


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

    def printnode_print(self, job):
        """Send a job built by ``ir.actions.report.get_print_jobs`` to PrintNode."""
        self.ensure_one()
        if self.type != "printnode" or not self.printnode_account_id:
            raise UserError(self.env._("Must be a PrintNode printer"))
        jobtype = job.get("printnode_type")
        if jobtype not in ("pdf", "txt"):
            raise UserError(self.env._("Jobtype %s not implemented for Print Node", job.get("report_type")))
        return self.printnode_account_id.sudo()._print_node_submit_job(
            printerid=self.printnode_identifier,
            jobtype=jobtype,
            content=job["report"],
        )

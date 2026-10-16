from odoo import api, fields, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    iot_rule_ids = fields.One2many("ir.actions.report.iot.rule", "report_id", string="IoT Report Rules")

    def report_action(self, docids, data=None, config=True):
        result = super().report_action(docids, data, config)
        if result.get("type") != "ir.actions.report":
            return result
        if user_rule := self.iot_rule_ids.filtered(lambda r: r.user_id == self.env.user):
            result["id"] = self.id
            result["device_ids"] = user_rule.device_id.mapped("identifier")
        elif self.env.user.iot_device_id:
            result["id"] = self.id
            result["device_ids"] = self.env.user.iot_device_id.mapped("identifier")

        return result


class IrActionsReportIotRule(models.Model):
    _name = "ir.actions.report.iot.rule"
    _description = "Report IoT Rule"

    report_id = fields.Many2one("ir.actions.report", required=True)
    user_id = fields.Many2one(
        "res.users",
        required=True,
    )
    device_id = fields.Many2one("iot.device", ondelete="set null", domain="[('type', '=', 'printer')]")
    skip_dialog = fields.Boolean(default=True)
    active = fields.Boolean(default=True)

    _unique_report_users = models.Constraint(
        "UNIQUE(report_id, user_id)",
        "Only can have one IoT rule per report and user.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env["iot.channel"].sudo().send_message(
            {
                "user_ids": res.mapped("user_id").ids,
                "report_ids": res.mapped("report_id").ids,
            },
            "clear_local_storage",
        )
        return res

    def write(self, vals):
        res = super().write(vals)
        self.env["iot.channel"].sudo().send_message(
            {
                "user_ids": self.mapped("user_id").ids,
                "report_ids": self.mapped("report_id").ids,
            },
            "clear_local_storage",
        )
        return res

from odoo import fields, models


class iotDevice(models.Model):
    _inherit = "iot.device"

    iot_report_rule_ids = fields.One2many(
        "ir.actions.report.iot.rule",
        "device_id",
    )

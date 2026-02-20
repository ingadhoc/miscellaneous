from odoo import _, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def render_document(self, device_id_list, res_ids, data=None):
        result = super().render_document(device_id_list, res_ids, data)
        filtered_result = []
        for item in result:
            iot_box = self.env["iot.box"].browse(item["iotBoxId"])
            if iot_box.print_node_api_key:
                job = iot_box._print_node_submit_job(
                    printerid=item["deviceIdentifier"],
                    jobtype=self.report_type,
                    content=item["document"],
                )
                if job:
                    device = iot_box.device_ids.filtered(lambda d: d.identifier == item["deviceIdentifier"])
                    printer_name = device.name if device else _("Printer")
                    self.env.user._bus_send(
                        "simple_notification",
                        {
                            "type": "success",
                            "message": _("Print job successfully sent to %s via PrintNode", printer_name),
                        },
                    )
            else:
                filtered_result.append(item)
        return filtered_result

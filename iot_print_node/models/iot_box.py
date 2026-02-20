import base64
import logging
import time
import uuid

import requests
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PRINTNODE_URL = "https://api.printnode.com"
TIMEOUT = 20


class IotBox(models.Model):
    _inherit = "iot.box"

    print_node_api_key = fields.Char("Print Node API Key", readonly=True)

    def open_homepage(self):
        self.ensure_one()
        if self.print_node_api_key:
            return {
                "type": "ir.actions.act_url",
                "url": "https://api.printnode.com/app/print",
                "target": "new",
            }
        return super().open_homepage()

    @api.model
    def _get_response(self, service, data=None):
        request_url = f"{PRINTNODE_URL}/{service}"
        headers = {
            "authorization": "Basic " + base64.b64encode(self.print_node_api_key.encode("UTF-8")).decode("UTF-8"),
        }
        try:
            if data:
                headers["Content-Type"] = "application/json"
                response = requests.post(request_url, json=data, headers=headers, timeout=TIMEOUT)
                response.raise_for_status()
            else:
                response = requests.get(request_url, headers=headers, timeout=TIMEOUT)
                response.raise_for_status()
        except requests.RequestException:
            raise UserError(_("Could not connect to print node. Check your configuration"))
        return response.json()

    def action_print_update_devices(self):
        _logger.info("Updating Print Node Printers")
        devices = self._get_response("printers")
        device_commands = []
        existing_devices = self.device_ids.mapped("identifier")

        for pn_printer in devices:
            vals = {
                "name": pn_printer["description"],
                "identifier": str(pn_printer["id"]),
                "type": "printer",
                "connection": "printnode_printer",
                "connected_status": "connected" if pn_printer["state"] == "online" else "disconnected",
            }
            if str(pn_printer["id"]) in existing_devices:
                del existing_devices[existing_devices.index(str(pn_printer["id"]))]

            if device_id := self.device_ids.filtered(lambda d: d.identifier == str(pn_printer["id"])):
                device_commands.append(Command.update(device_id.id, vals))
            else:
                device_commands.append(Command.create(vals))

        for to_deleted_devices in existing_devices:
            device_commands.append(
                Command.delete(self.device_ids.filtered(lambda d: d.identifier == to_deleted_devices).id)
            )
        self.sudo().device_ids = device_commands

    def _print_node_submit_job(self, printerid, jobtype, content):
        """Submit a job to printerid with content of dataUrl.

        Args:
            printerid: string, the printer id to submit the job to.
            jobtype: string, must match the dictionary keys in content and
                content_type.
            jobsrc: string, points to source for job. Could be a pathname or
                id string.
        Returns:
            boolean: True = submitted, False = errors.
        """
        if jobtype in ["qweb-pdf", "pdf", "aeroo"]:
            jobtype = "pdf"
        elif jobtype in ["qweb-text"]:
            jobtype = "txt"
        else:
            raise UserError(_("Jobtype %s not implemented for Print Node") % (jobtype))

        # Generate a unique title using timestamp and microseconds
        title = f"odoo_print_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        data = {
            "printerId": printerid,
            "title": title,
            "contentType": "pdf_base64" if jobtype == "pdf" else "raw_base64",
            "content": content.decode("utf-8"),
            "source": "created by odoo db: %s" % self.env.cr.dbname,
        }
        return self._get_response("printjobs", data)

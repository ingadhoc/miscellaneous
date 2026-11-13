import base64
import logging
import time
import uuid

import requests
from odoo import Command, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PRINTNODE_URL = "https://api.printnode.com"
TIMEOUT = 20


class PrintnodeAccount(models.Model):
    _name = "printnode.account"
    _description = "PrintNode Account"

    name = fields.Char(required=True)
    print_node_api_key = fields.Char("Print Node API Key", required=True, groups="base.group_system")
    printer_ids = fields.One2many("printer.printer", "printnode_account_id", string="Printers")
    printer_count = fields.Integer(compute="_compute_printer_count")

    @api.depends("printer_ids")
    def _compute_printer_count(self):
        for account in self:
            account.printer_count = len(account.printer_ids)

    def action_open_printnode(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "https://api.printnode.com/app/print",
            "target": "new",
        }

    def _get_response(self, service, data=None):
        self.ensure_one()
        request_url = f"{PRINTNODE_URL}/{service}"
        api_key = self.sudo().print_node_api_key
        headers = {
            "authorization": "Basic " + base64.b64encode(api_key.encode("UTF-8")).decode("UTF-8"),
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
            raise UserError(self.env._("Could not connect to print node. Check your configuration"))
        return response.json()

    def action_print_update_devices(self):
        self.ensure_one()
        _logger.info("Updating Print Node Printers")
        pn_printers = self._get_response("printers")
        printer_commands = []
        existing_identifiers = self.printer_ids.mapped("printnode_identifier")

        for pn_printer in pn_printers:
            identifier = str(pn_printer["id"])
            vals = {
                "name": pn_printer["description"],
                "type": "printnode",
                "printnode_identifier": identifier,
                "printnode_status": "connected" if pn_printer["state"] == "online" else "disconnected",
            }
            if identifier in existing_identifiers:
                existing_identifiers.remove(identifier)

            printer = self.printer_ids.filtered(lambda p, identifier=identifier: p.printnode_identifier == identifier)
            if printer:
                printer_commands.append(Command.update(printer.id, vals))
            else:
                printer_commands.append(Command.create(vals))

        for identifier in existing_identifiers:
            printer = self.printer_ids.filtered(lambda p, identifier=identifier: p.printnode_identifier == identifier)
            printer_commands.append(Command.delete(printer.id))
        self.sudo().printer_ids = printer_commands

    def _print_node_submit_job(self, printerid, jobtype, content):
        """Submit a job to printerid with content of dataUrl.

        Args:
            printerid: string, the printer id to submit the job to.
            jobtype: string, "pdf" or "txt".
            content: string, the document encoded in base64.
        Returns:
            dict: the PrintNode response.
        """
        # Generate a unique title using timestamp and microseconds
        title = f"odoo_print_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

        data = {
            "printerId": printerid,
            "title": title,
            "contentType": "pdf_base64" if jobtype == "pdf" else "raw_base64",
            "content": content,
            "source": f"created by odoo db: {self.env.cr.dbname}",
        }
        return self._get_response("printjobs", data)

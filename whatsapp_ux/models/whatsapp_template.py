##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class WhatsappTemplate(models.Model):
    _inherit = "whatsapp.template"

    bulk_send_action = fields.Boolean(
        default=True,
        help="Automatically create a one-click bulk send server action on the "
        "list view of this template's model once the template is approved. The "
        "action reuses the native WhatsApp batch queue, so it sends the template "
        "to every selected record at once.",
    )

    def _get_bulk_send_action(self):
        """Return the bulk send server action linked to this template, if any."""
        self.ensure_one()
        return (
            self.env["ir.actions.server"]
            .sudo()
            .search(
                [
                    ("wa_template_id", "=", self.id),
                    ("binding_model_id", "=", self.model_id.id),
                ],
                limit=1,
            )
        )

    def _sync_bulk_send_action(self):
        """Create or remove the one-click bulk send server action so that it
        exists exactly for approved templates that opted in."""
        for template in self:
            action = template._get_bulk_send_action()
            should_exist = template.status == "approved" and template.bulk_send_action and template.model_id
            if should_exist and not action:
                self.env["ir.actions.server"].sudo().create(
                    {
                        "name": _("Send by WhatsApp: %s", template.name),
                        "model_id": template.model_id.id,
                        "binding_model_id": template.model_id.id,
                        "binding_view_types": "list",
                        "state": "whatsapp",
                        "wa_template_id": template.id,
                    }
                )
            elif not should_exist and action:
                action.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._sync_bulk_send_action()
        return templates

    def write(self, vals):
        res = super().write(vals)
        if {"status", "bulk_send_action", "model_id"} & set(vals):
            self._sync_bulk_send_action()
        return res

    def unlink(self):
        # ``wa_template_id`` on ir.actions.server has ondelete='restrict', so the
        # linked actions must be removed before the templates can be deleted.
        self.env["ir.actions.server"].sudo().search([("wa_template_id", "in", self.ids)]).unlink()
        return super().unlink()

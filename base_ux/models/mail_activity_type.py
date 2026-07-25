##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_quick_activity_types(self):
        """Devuelve las primeras N actividades ordenadas por sequence, para mostrar
        como badges de acceso rápido. N sale del parámetro del sistema
        base_ux.activity_quick_badges (por defecto 5)."""
        limit_param = self.env["ir.config_parameter"].sudo().get_param("base_ux.activity_quick_badges", "5")
        return self.search([], order="sequence, id", limit=int(limit_param))

##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    quick_activity_ids = fields.Many2many(
        "mail.activity.type",
        compute="_compute_quick_activity_ids",
        help="IDs de los tipos de actividad más frecuentes para mostrar como badges.",
    )

    @api.depends_context("uid")
    def _compute_quick_activity_ids(self):
        """Obtiene las primeras N actividades ordenadas por sequence."""
        # Obtener el límite desde parámetros del sistema (por defecto 5)
        limit_param = self.env["ir.config_parameter"].sudo().get_param("base_ux.activity_quick_badges", "5")
        limit = int(limit_param)
        quick_types = self.env["mail.activity.type"].search([], order="sequence, id", limit=limit)
        for record in self:
            record.quick_activity_ids = quick_types

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
        quick_types = self.env["mail.activity.type"]._get_quick_activity_types()
        for record in self:
            record.quick_activity_ids = quick_types

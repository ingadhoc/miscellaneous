##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    quick_activity_ids = fields.Many2many(
        "mail.activity.type",
        compute="_compute_quick_activity_ids",
        help="IDs de los tipos de actividad más frecuentes para mostrar como badges.",
    )

    @api.depends("activity_type_id")
    @api.depends_context("uid")
    def _compute_quick_activity_ids(self):
        """Las primeras N actividades por sequence, más el tipo ya seteado en la actividad.
        Incluir el tipo actual es necesario al editar una actividad existente: si su tipo no
        está entre los N sugeridos, el badge de la selección vigente no se renderizaría y
        visualmente se perdería el valor guardado."""
        quick_types = self.env["mail.activity.type"]._get_quick_activity_types()
        for record in self:
            record.quick_activity_ids = quick_types | record.activity_type_id

    @api.onchange("activity_type_id")
    def _onchange_activity_type_id(self):
        """overrides original method: keep the activity description when
        changing the activity type, regardless of the activity type's description,
        and change the activity user only if the activity type has a default user"""
        note = self.note
        user = self.user_id
        super()._onchange_activity_type_id()
        if user and user != self.user_id and not self.activity_type_id.default_user_id:
            self.user_id = user
        if note != "<p><br></p>" and note != False and note != self.note:
            self.note = note

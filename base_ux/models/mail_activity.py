##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.onchange('activity_type_id')
    def _onchange_activity_type_id(self):
        """ overrides original method: keep the activity description when
        changing the activity type, regardless of the activity type's description,
        and change the activity user only if the activity type has a default user """
        note = self.note
        user = self.user_id
        super()._onchange_activity_type_id()
        if user and user != self.user_id and not self.activity_type_id.default_user_id:
            self.user_id = user
        if note != '<p><br></p>' and note != False and note != self.note:
            self.note = note

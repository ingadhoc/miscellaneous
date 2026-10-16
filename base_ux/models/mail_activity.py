##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models
from odoo.tools import is_html_empty


class MailActivity(models.Model):
    _inherit = "mail.activity"

    @api.depends("activity_type_id")
    def _compute_note(self):
        """Keep the note already written when the activity type changes, regardless of
        the default note of the new activity type."""
        super(MailActivity, self.filtered(lambda a: is_html_empty(a.note)))._compute_note()

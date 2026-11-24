from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    run_automatically = fields.Boolean(
        help="If checked, when the due date is reached, the email templates of the activity type are sent "
        "and the activity is marked as done."
    )

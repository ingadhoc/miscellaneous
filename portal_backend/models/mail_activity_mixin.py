from odoo import models, fields


class MailActivityMixin(models.AbstractModel):
    _inherit = 'mail.activity.mixin'

    activity_ids = fields.One2many(
        groups="base.group_user, portal_backend.group_portal_backend",
    )
    activity_state = fields.Selection(
        groups="base.group_user, portal_backend.group_portal_backend",
    )
    activity_user_id = fields.Many2one(
        groups="base.group_user, portal_backend.group_portal_backend",
    )
    activity_type_id = fields.Many2one(
        groups="base.group_user, portal_backend.group_portal_backend",
    )
    activity_date_deadline = fields.Date(
        groups="base.group_user, portal_backend.group_portal_backend",
    )
    activity_summary = fields.Char(
        groups="base.group_user, portal_backend.group_portal_backend",
    )

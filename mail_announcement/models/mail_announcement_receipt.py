from odoo import fields, models


class MailAnnouncementReceipt(models.Model):
    _name = "mail.announcement.receipt"
    _description = "Announcement Read Receipt"
    _order = "read_date desc, id desc"

    announcement_id = fields.Many2one(
        comodel_name="mail.announcement",
        string="Announcement",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
    )
    is_read = fields.Boolean(
        string="Read",
        default=False,
    )
    read_date = fields.Datetime(
        string="Read Date",
        readonly=True,
    )

    _unique_user_announcement = models.Constraint(
        "UNIQUE(announcement_id, user_id)",
        "Each user can only have one read receipt per announcement.",
    )

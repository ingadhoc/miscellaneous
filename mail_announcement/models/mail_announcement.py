from odoo import api, fields, models


class MailAnnouncement(models.Model):
    _name = "mail.announcement"
    _description = "Important Announcement"
    _order = "date desc"

    name = fields.Char(
        string="Subject",
        required=True,
    )
    body = fields.Html(
        string="Content",
        required=True,
        sanitize=True,
    )
    author_id = fields.Many2one(
        comodel_name="res.users",
        string="Author",
        default=lambda self: self.env.user,
        required=True,
        ondelete="restrict",
    )
    channel_id = fields.Many2one(
        comodel_name="discuss.channel",
        string="Channel/Origin",
        ondelete="set null",
    )
    date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        required=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("sent", "Sent")],
        string="Status",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
    )
    recipient_ids = fields.Many2many(
        comodel_name="res.users",
        relation="mail_announcement_res_users_rel",
        column1="announcement_id",
        column2="user_id",
        string="Recipients",
    )
    receipt_ids = fields.One2many(
        comodel_name="mail.announcement.receipt",
        inverse_name="announcement_id",
        string="Read Receipts",
    )
    receipt_count = fields.Integer(
        compute="_compute_receipt_stats",
        string="Total Recipients",
    )
    pending_receipt_count = fields.Integer(
        compute="_compute_receipt_stats",
        string="Pending",
    )
    is_pending_for_me = fields.Boolean(
        compute="_compute_is_pending_for_me",
        search="_search_is_pending_for_me",
        string="Pending for Me",
    )

    @api.depends("receipt_ids.is_read")
    def _compute_receipt_stats(self):
        for rec in self:
            rec.receipt_count = len(rec.receipt_ids)
            rec.pending_receipt_count = len(rec.receipt_ids.filtered(lambda r: not r.is_read))

    @api.depends("receipt_ids.is_read", "receipt_ids.user_id")
    def _compute_is_pending_for_me(self):
        user = self.env.user
        for rec in self:
            my_receipt = rec.receipt_ids.filtered(lambda r: r.user_id == user)
            rec.is_pending_for_me = bool(my_receipt) and not my_receipt[:1].is_read

    def _search_is_pending_for_me(self, operator, value):
        user = self.env.user
        pending_ids = (
            self.env["mail.announcement.receipt"]
            .search([("user_id", "=", user.id), ("is_read", "=", False)])
            .announcement_id.ids
        )
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [("id", "in", pending_ids)]
        return [("id", "not in", pending_ids)]

    @api.onchange("channel_id")
    def _onchange_channel_id(self):
        if self.channel_id:
            partner_ids = self.channel_id.channel_member_ids.partner_id.ids
            channel_users = self.env["res.users"].search([("partner_id", "in", partner_ids), ("share", "=", False)])
            self.recipient_ids = channel_users
        else:
            self.recipient_ids = False

    def _get_recipients(self):
        """Return the full set of users that must receive this announcement."""
        self.ensure_one()
        recipients = self.recipient_ids
        if self.channel_id:
            partner_ids = self.channel_id.channel_member_ids.partner_id.ids
            channel_users = self.env["res.users"].search([("partner_id", "in", partner_ids), ("share", "=", False)])
            recipients = recipients | channel_users
        return recipients

    def action_send(self):
        self.ensure_one()
        if self.state == "sent":
            return
        recipients = self._get_recipients()
        existing_user_ids = self.receipt_ids.user_id.ids
        vals_list = [
            {
                "announcement_id": self.id,
                "user_id": user.id,
                "is_read": False,
            }
            for user in recipients
            if user.id not in existing_user_ids
        ]
        if vals_list:
            self.env["mail.announcement.receipt"].sudo().create(vals_list)
        self.write({"state": "sent"})

    def action_mark_as_read(self):
        for rec in self:
            receipt = rec.receipt_ids.filtered(lambda r: r.user_id == self.env.user)
            if receipt:
                receipt.write({"is_read": True, "read_date": fields.Datetime.now()})
            else:
                self.env["mail.announcement.receipt"].create(
                    {
                        "announcement_id": rec.id,
                        "user_id": self.env.user.id,
                        "is_read": True,
                        "read_date": fields.Datetime.now(),
                    }
                )

from odoo import models
import re


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_create(self, values_list):
        if 'partner_ids' in values_list:
            xml_id = 'mail_internal.internal_followers'
            rec_id = self.env.ref(xml_id).id
            if rec_id in values_list['partner_ids']:
                add = list(values_list['partner_ids'])
                add.remove(rec_id)
                for follower in self.message_follower_ids.filtered(lambda x: x.partner_id.user_ids):
                    if (follower.partner_id.id not in values_list['partner_ids'] and
                            follower.partner_id.id != values_list['author_id']):
                        add.append(follower.partner_id.id)
                values_list['partner_ids'] = set(add)
                values_list['body'] = self.edit_body(values_list['body'], add)
        return super()._message_create(values_list)

    def edit_body(self, body, partner_ids):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ""
        partner_string = ""
        for partner_id in partner_ids:
            href = "http://{}/web#model=res.partner&id={}".format(base_url, partner_id)
            partner = self.env['res.partner'].browse(partner_id)
            partner_string += """
                <a href='{}' class='o_mail_redirect' data-oe-id='{}' data-oe-model='res.partner' target='_blank'>@{}</a> 
                """.format(href, partner_id, partner.name)
        body = re.sub("<a.*@Internal Followers</a>", partner_string, body)
        return body

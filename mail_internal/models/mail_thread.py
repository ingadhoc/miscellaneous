from lxml import etree

from odoo import api, models
from odoo.tools.safe_eval import safe_eval


class MailThread(models.AbstractModel):

    _inherit = 'mail.thread'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        res = super(MailThread, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='message_ids']"):
                # the 'Internal message' button is employee only
                options = safe_eval(node.get('options', '{}'))
                is_employee = self.env.user.has_group('base.group_user')
                options['display_internal_button'] = is_employee
                # save options on the node
                node.set('options', repr(options))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

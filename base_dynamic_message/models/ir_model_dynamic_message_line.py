from odoo import models, fields, api
import re


class IrModelDynamicMessageLine(models.Model):
    _name = 'ir.model.dynamic_message.line'
    _description = 'ir.model.dynamic_message.line'

    dynamic_message_id = fields.Many2one('ir.model.dynamic_message', required=True, ondelete='cascade')
    description = fields.Text()
    domain = fields.Char()
    message = fields.Html(required=True,)
    model_name = fields.Char(related='dynamic_message_id.model_id.model')
    code = fields.Text(compute='_compute_code', store=True, readonly=False)

    @api.depends('message', 'domain')
    def _compute_code(self):
        for rec in self:
            if rec.domain:
                # si el doinio tiene expresiones "EXP:" recorremos las tuplas y lo dejamos sin string y limpiamos el "EXP:""
                domain = rec.domain
                if "EXP:" in rec.domain:
                    # construido con chatgpt
                    # Original string
                    # Regular expression pattern to extract the expression parts
                    pattern = r'"EXP: (.+?)"'

                    matches = re.finditer(pattern, domain)

                    for match in matches:
                        expression = match.group(1)
                        domain = domain.replace(f'"EXP: {expression}"', expression)

                rec.code = """
if rec in rec.filtered_domain(%s):
    messages.append('%s')
""" % (domain, str(rec.message).replace('<p>', '').replace('</p>', ''))
            else:
                rec.code = False
                # code = self.filtered_domain(self.env['account.payment.method']._get_payment_method_domain(payment_method_code))

from odoo import api, models, fields

class OkrBase(models.Model):
    _description = 'OKR BASE'
    _name = "okr.base"

    name = fields.Char(required=True)
    description = fields.Char()
    user_id = fields.Many2one('res.users')
    completed_percentage = fields.Float(compute='_compute_completed_percentage')
    type = fields.Selection(selection=[('commitment', 'commitment'),('inspirational', 'inspirational')], required=True)
    kr_line_ids = fields.One2many('okr.base.line', 'okr_base_id')

    def _compute_completed_percentage(self):
        for kr in self:
            if kr.kr_line_ids:
                w_cum = 0
                sum_weigh = 0
                for krl in kr.kr_line_ids:
                    w_cum += krl.completed_percentage*krl.weight
                    sum_weigh += krl.weight
                if sum_weigh>0:
                    kr.completed_percentage = w_cum/sum_weigh
                else:
                    kr.completed_percentage = 0
            else:
                kr.completed_percentage = 0



class OkrBaseLine(models.Model):
    _description = 'OKR LINE'
    _name = "okr.base.line"

    name = fields.Char()
    description = fields.Char()
    user_id = fields.Many2one('res.users')
    okr_base_id = fields.Many2one(comodel_name='okr.base', required=True)
    actual_value = fields.Float()
    weight = fields.Float()
    target = fields.Float()
    completed_percentage = fields.Float(compute='_compute_completed_percentage_line')

    def _compute_completed_percentage_line(self):
        for kr in self:
            kr.completed_percentage = 0
            if kr.actual_value>0 and kr.actual_value<kr.target:
                kr.completed_percentage = (kr.actual_value/kr.target)
            else:
                kr.completed_percentage = 1

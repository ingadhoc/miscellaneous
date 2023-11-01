from odoo import api, models, fields

class OkrBase(models.Model):
    _description = 'OKR BASE'
    _name = "okr.base"

    name = fields.Char()
    completed_percentage = fields.Float(compute='_compute_completed_percentage')
    kr_line_ids = fields.One2many('okr.base.line', 'okr_base_id')

    def _compute_completed_percentage(self):
        for kr in self:
            if kr.kr_line_ids:
                cum = 0
                cant = 0
                for krl in kr.kr_line_ids:
                    cum += krl.completed_percentage
                    cant += 1
                kr.completed_percentage = cum/cant
            else:
                kr.completed_percentage = 0



class OkrBaseLine(models.Model):
    _description = 'OKR LINE'
    _name = "okr.base.line"

    name = fields.Char()
    okr_base_id = fields.Many2one(comodel_name='okr.base', required=True)
    actual_value = fields.Float()
    target = fields.Float()
    completed_percentage = fields.Float(compute='_compute_completed_percentage_line')

    def _compute_completed_percentage_line(self):
        for kr in self:
            kr.completed_percentage = 0
            if kr.actual_value>0 and kr.actual_value<kr.target:
                kr.completed_percentage = (kr.actual_value/kr.target)
            else:
                kr.completed_percentage = 1


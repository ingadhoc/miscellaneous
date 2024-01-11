from odoo import api, models,fields


class OkrResults(models.Model):
    _name = 'okr.results'
    _description= 'Resultados Okr'
    _order = "id desc"

    name= fields.Char(required=True,)
    description = fields.Text()
    area = fields.Selection([('i+d', 'I+D'),('aministracion','Administración'),('rrhh', 'Recursos Humanos'), ('ventas', 'Ventas'),('consultoria', 'Consultoria'),('mdea','Mesa de Ayuda'), ('adhoc','Adhoc')])
    number_q = fields.Integer(string='Número de Q')
    progress = fields.Float(compute="_compute_progress")
    type = fields.Selection([('commitment', 'Commitment'), ('inspiring', 'Inspiring')])
    weight = fields.Float()
    responsible = fields.Many2one('res.users')
    target = fields.Integer(required=True, default=0)
    users_id = fields.Many2one('res.users')
    results = fields.Integer()

    @api.depends('results', 'target')
    def _compute_progress(self):
        for rec in self:
            if rec.results and rec.target:
                rec.progress = (rec.results / rec.target)*100
            else:
                rec.progress = 0

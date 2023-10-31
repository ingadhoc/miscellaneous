from odoo import models, api, fields
import time
from odoo.exceptions import UserError


class OkrObjetivo(models.Model):
    _name = "okr.objetivo"
    _description = "Objetivo"
    _rec_name = 'resumen_objetivo'

    resumen_objetivo = fields.Many2one('kr.ppal', string="KR ppal", required=True)
    descripcion_ampliada = fields.Char(string="Descripcion ampliada", required=True, readonly=False)
    progreso = fields.Integer(string="Progress", compute='_compute_progreso',help="Progress from zero knowledge (0%) to fully mastered (100%).", default=0)
    peso = fields.Selection([('inspiracional', 'Inspiracional'), ('commitment', 'Commitment')])
    comentarios = fields.Char()
    okr_ids = fields.One2many('okr.objetivo.line', 'objetivo_padre')
    team = fields.Selection([('imasd', 'I+D'), ('administracion', 'Administración'), ('rechumanos', 'Recursos Humanos'), ('ventas', 'Ventas'), ('mdea', 'Mdea'), ('consultoria', 'Consultoria')], required=True)
    periodo = fields.Selection([('q1', 'Q1'), ('q2', 'Q2'), ('q3', 'Q3'), ('q4', 'Q4')], required=True)
    state = fields.Selection([('in_progress', 'En progreso'), ('cancel', 'Cancelado'), ('state', 'finalizado')])
    year = fields.Char(
        required=True,
        default=time.strftime('%Y'),
    )

    @api.depends('okr_ids')
    def _compute_progreso(self):
        sumatory = sum(self.okr_ids.mapped('progreso')) or 0
        self.progreso = sumatory
        if sumatory > 100:
            raise UserError("Revisar el progreso de los kr, no puede ser mayor a 100")

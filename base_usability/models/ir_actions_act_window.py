# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class IrActionsAct_window(models.Model):
    _inherit = 'ir.actions.act_window'

    ir_values_id = fields.Many2one(
        comodel_name='ir.values',
        string='Ir Values',
        compute='_compute_ir_values'
    )

    @api.multi
    @api.depends('name', 'src_model')
    def _compute_ir_values(self):
        """ Solo si hay src_model puede haber accion ligada"""
        for rec in self.filtered(lambda x: x.src_model):
            rec.ir_values_id = rec.ir_values_id.search([
                ('value', '=', "ir.actions.act_window,%s" % rec.id),
                ('model', '=', rec.src_model)],
                # ('name', '=', rec.name), ('model', '=', rec.src_model)],
                limit=1)

    @api.multi
    def create_action(self):
        """ Create a contextual action for each act window. """
        for rec in self:
            ir_values = self.env['ir.values'].sudo().create({
                'name': rec.name,
                'model': rec.src_model,
                'key2': 'client_action_multi',
                'value': "ir.actions.act_window,%s" % rec.id,
            })
            rec.write({'ir_values_id': ir_values.id})
        return True

    @api.multi
    def unlink_action(self):
        """ Remove the contextual actions created for the act window. """
        self.check_access_rights('write', raise_exception=True)
        for rec in self:
            if rec.ir_values_id:
                try:
                    rec.ir_values_id.sudo().unlink()
                except Exception:
                    raise UserError(_('Deletion of the action record failed.'))
        return True

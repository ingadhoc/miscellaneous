from odoo import models, api


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.multi
    def create_action(self):
        """ Create a contextual action for each act window. """
        model = self.env['ir.model']
        for rec in self.filtered('src_model'):
            src_model = model.search([('model', '=', rec.src_model)])
            rec.write({'binding_model_id': src_model.id,
                       'binding_type': 'action'})
        return True

    @api.multi
    def unlink_action(self):
        """ Remove the contextual actions created for the act window. """
        self.check_access_rights('write', raise_exception=True)
        self.filtered('binding_model_id').write({'binding_model_id': False})
        return True

    @api.onchange('src_model')
    def update_binding_model_id(self):
        self.binding_model_id = False

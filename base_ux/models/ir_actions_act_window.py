from odoo import models, api


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def create_action(self):
        """ Create a contextual action for each act window. """
        model = self.env['ir.model']
        for rec in self.filtered('res_model'):
            res_model = model.search([('model', '=', rec.res_model)])
            rec.write({'binding_model_id': res_model.id,
                       'binding_type': 'action'})
        return True

    def unlink_action(self):
        """ Remove the contextual actions created for the act window. """
        self.check_access_rights('write', raise_exception=True)
        self.filtered('binding_model_id').write({'binding_model_id': False})
        return True

    @api.onchange('res_model')
    def update_binding_model_id(self):
        self.binding_model_id = False

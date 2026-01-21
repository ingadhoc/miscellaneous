from odoo import api, models, fields


class IntegratorScriptLine(models.Model):
    # TODO rename to job everywhere
    _name = "integrator.integration.script_line"
    _description = "Odoo Integration Job"

    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    state = fields.Selection([
        ('pending', 'Pending'), ('enqueued', 'Enqueued'), ('started', 'Started'),
        ('done', 'Done'), ('failed', 'Failed')], required=True, default='pending')
    next_offset = fields.Integer()
    integration_id = fields.Many2one(
        "integrator.integration", string="Integration", ondelete="cascade",
        required=True)
    script_id = fields.Many2one(
        "integrator.integration.script", string="Script", ondelete="restrict",
        required=True, context={'active_test': False})

    _sql_constraints = [
        ('script_line_unique', 'unique(integration_id, script_id)',
         "You can't add the same script twice")
    ]

    @api.depends('integration_id')
    def odoo_run_script_now(self):
        self.ensure_one()
        self.integration_id.odoo_run_job(self)
        return True

from odoo import models, fields, api
import ast
import textwrap


class IrModelDynamicMessage(models.Model):
    _name = 'ir.model.dynamic_message'
    _description = 'ir.model.dynamic_message'

    name = fields.Char(required=True)
    description = fields.Text()
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Name')
    line_ids = fields.One2many('ir.model.dynamic_message.line', 'dynamic_message_id', copy=True)
    code = fields.Text(compute='_compute_code')
    depends = fields.Char(compute='_compute_depends', store=True, readonly=False, required=True)
    field_id = fields.Many2one('ir.model.fields', readonly=True, copy=False)
    view_to_inherit_id = fields.Many2one(
        'ir.ui.view', compute='_compute_view_to_inherit', readonly=False, store=True, required=True)
    view_id = fields.Many2one('ir.ui.view', readonly=True, copy=False)
    alert_type = fields.Selection([('info', 'info'), ('warning', 'warning'), ('danger', 'danger')], required=True, default='info')

    @api.depends('model_id')
    def _compute_view_to_inherit(self):
        for rec in self:
            rec.view_to_inherit_id = rec.env['ir.ui.view'].search(
                [('type', '=', 'form'), ('model', '=', rec.model_id.model), ('mode', '=', 'primary')], limit=1)

    @api.depends('line_ids.code')
    def _compute_code(self):
        for rec in self:
            sub_string = ''.join(rec.line_ids.filtered('code').mapped('code'))
            sub_string = textwrap.indent(sub_string, prefix='    ')
            field_name = 'x_dynamic_message_%i' % rec._origin.id or 0
            rec.code = """
for rec in self:
    messages = []
%s
    if not messages:
        rec['%s'] = False
    else:
        rec['%s'] = "<ul>%%s</ul>" %% "".join(["<li>%%s</li>" %% message for message in messages])
""" % (sub_string, field_name, field_name)

    @api.depends('line_ids.domain')
    def _compute_depends(self):
        for rec in self:
            dep_fields = []
            for line in rec.line_ids.filtered('domain'):
                domain = ast.literal_eval(line.domain)
                for element in domain:
                    if type(element) is not tuple:
                        continue
                    # TODO deberiamos chequear que el campo sea sercheable (en smart search teniamos algo de esto)
                    if '.' in element[0]:
                        dep_fields.append(element[0].split('.')[0])
                    elif element[0] != 'id':
                        dep_fields.append(element[0])
            rec.depends = ','.join(list(set(dep_fields))) if dep_fields else False

    def confirm(self):
        for rec in self:
            field_name = 'x_dynamic_message_%i' % rec.id
            field_vals = {
                'name': field_name,
                'field_description': 'Dynamic Message',
                'state': 'manual',
                'store': False,
                'ttype': 'html',
                'model_id': rec.model_id.id,
                'compute': rec.code,
                'depends': rec.depends,
            }
            if rec.field_id:
                rec.field_id.sudo().write(field_vals)
            else:
                rec.field_id = rec.field_id.sudo().create(field_vals)

            view_vals = {
                'name': 'Dynamic Message for %s' % rec.model_id.name,
                'inherit_id': rec.view_to_inherit_id.id,
                'model': rec.model_id.model,
                'priority': 999,
                'arch_db': """
<sheet position="before">
    <div class="alert alert-%s mb-0" role="alert" invisible="not %s">
        <field name="%s" nolabel="1" readonly="1"/>
    </div>
</sheet>
""" % (rec.alert_type, field_name, field_name),
            }
            if rec.view_id:
                rec.view_id.sudo().write(view_vals)
            else:
                rec.view_id = rec.view_id.sudo().create(view_vals)

    @api.ondelete(at_uninstall=True)
    def _delete_field_and_view(self):
        self.mapped('field_id').sudo().unlink()
        self.mapped('view_id').sudo().unlink()

    _sql_constraints = [
        (
            'unique_level_per_model', 'UNIQUE(model_id, alert_type, view_to_inherit_id)',
            'Debe haber un unico registro por modelo, vista heredada y tipo de alerta')
    ]

##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)

try:
    from openupgradelib import openupgrade_merge_records
except (ImportError, IOError) as err:
    _logger.debug(err)


class MergeRecordsLineAttribute(models.TransientModel):

    _name = 'merge.records.line.attribute'

    name = fields.Char()
    value = fields.Char()
    wizard_line_id = fields.Many2one(
        'merge.records.line',
        ondelete='cascade',
    )

    @api.depends('name', 'value')
    def name_get(self):
        return [
            (rec.id, (' %s: %s' % (
                rec.name, rec.value or _('Do not apply'))))
            for rec in self]


class MergeRecordsLine(models.TransientModel):

    _name = 'merge.records.line'
    _order = 'xml_id'

    wizard_id = fields.Many2one(
        'merge.records',
        ondelete='cascade',
    )
    name = fields.Char()
    res_id = fields.Integer(
        string='ID',
        help="ID of the target record in the database",
    )
    res_name = fields.Char(
        'Record Name',
    )
    model = fields.Char(
        string='Model Name',
        required=True,
    )
    xml_id = fields.Char(
        'XML ID',
    )
    attribute_ids = fields.One2many(
        'merge.records.line.attribute',
        'wizard_line_id',
        string='Attributes',
    )


class MergeRecords(models.TransientModel):

    _name = 'merge.records'

    res_ids = fields.Char(
        string='Records to merge',
    )
    line_ids = fields.One2many(
        'merge.records.line',
        'wizard_id',
        string='Lines',
    )
    line_id = fields.Many2one(
        'merge.records.line',
        string='Final Record',
    )
    model_id = fields.Many2one(
        'ir.model',
        'Model',
        index=True,
        # required=True,
    )
    attribute_fields = fields.Char(
        'Attributes',
        readonly=True,  # TODO remove this when fix onchange
        help="Attributes to show in the wizard in order to make it easy to"
        " detect duplicated records",
    )

    @api.model
    def default_get(self, fields):
        res = super(MergeRecords, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        if active_model and active_ids:
            res.update({
                'model_id': self.env['ir.model'].search(
                    [('model', '=', active_model)]).id,
                'attribute_fields': '[]',
                'res_ids': active_ids,
            })
        return res

    @api.model
    def create(self, values):
        res = super(MergeRecords, self).create(values)
        res.line_ids = res.update_merge_lines()
        return res

    # TODO The update_merge_lines is working fine but for some reason this
    # onchange does not update the line_ids field properly (the attributes are
    # leave empty). if we use this wizard from interface in the future will be
    # good to fix this problem
    # @api.onchange('model_id', 'attribute_fields')
    # def onchange_merge_lines(self):
    #     for rec in self:
    #         rec.line_ids = rec.update_merge_lines()

    @api.multi
    def update_merge_lines(self):
        model = self.env[self.model_id.model] if self else self.env[
            self.env.context.get('active_model')]
        attribute_fields = self.attribute_fields if self else '[]'
        res_ids = safe_eval(self.res_ids) if (
            self and self.res_ids) else self.env.context.get('active_ids')
        res = []
        attribute_fields = safe_eval(attribute_fields)
        fields_data = model.fields_get(attribute_fields)
        for rec in model.browse(res_ids):
            xml_id = rec.get_external_id().get(rec.id)
            res += [(0, 0, {
                'name': '%s (%s)' % (rec.display_name, xml_id) if xml_id
                else rec.display_name,
                'res_name': rec.display_name,
                'res_id': rec.id,
                'xml_id': xml_id,
                'model': model._name,
                'attribute_ids': [] if not attribute_fields else [
                    (0, 0, {
                        'name': fields_data.get(key).get('string'),
                        'value':
                        value[-1] if isinstance(value, tuple) else value,
                    })
                    for key, value in rec.read(attribute_fields)[0].items()
                    if key != 'id'
                ],
            })]
        return res

    @api.multi
    def action_merge(self):
        """ Merge records button. Merge the selected records, and redirect to
            the merged record form view.
        """
        self.ensure_one()
        if not self.line_ids or len(self.line_ids) <= 1:
            raise UserError(_(
                "Please select at least two records"
            ))

        try:
            to_delete = self.line_ids - self.line_id
            openupgrade_merge_records.merge_records(
                env=self.env,
                model_name=self.model_id.model,
                record_ids=to_delete.mapped('res_id'),
                target_record_id=self.line_id.res_id,
            )
        except ValueError as error_singleton:
            if "Expected singleton" in repr(error_singleton):
                to_delete = self.line_ids - self.line_id
                for item in to_delete:
                    openupgrade_merge_records.merge_records(
                        env=self.env,
                        model_name=self.model_id.model,
                        record_ids=[item.res_id],
                        target_record_id=self.line_id.res_id,
                    )
        except Exception as error:
            raise UserError(_(
                "The records were not merge due to the next error: %s" %
                error))
        return True

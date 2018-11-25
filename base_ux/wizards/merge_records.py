##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError
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
    wizard_line_id = fields.Many2one('merge.records.line', 'Wizard Line')

    @api.depends('name', 'value')
    def name_get(self):
        return [
            (rec.id, (' %s: %s' % (
                rec.name, rec.value or _('Do not apply'))))
            for rec in self]


class MergeRecordsLine(models.TransientModel):

    _name = 'merge.records.line'
    _order = 'xml_id'

    wizard_id = fields.Many2one('merge.records', 'Wizard')
    name = fields.Char()
    res_id = fields.Many2one('res.country.state', 'Record Name')
    # TODO use res_id, res_model_id and res_model in order to make this generic
    xml_id = fields.Char('XML ID')
    attribute_ids = fields.One2many(
        'merge.records.line.attribute',
        'wizard_line_id',
        string='Attributes',
    )

    # TODO Improve: need to save the raw id, also the values in order to
    # have the history after merge.


class MergeRecords(models.TransientModel):

    _name = 'merge.records'

    line_ids = fields.One2many(
        'merge.records.line',
        'wizard_id',
        string='Lines',
    )
    line_id = fields.Many2one(
        'merge.records.line',
        string='Final Country State',
    )
    model_id = fields.Many2one('ir.model')

    @api.model
    def default_get(self, fields):
        res = super(MergeRecords, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        # TODO K this can be added as wizard parameter in order to made it
        # generic
        attribute_fields = ['code', 'country_id']
        fields_data = self.env[active_model].fields_get(attribute_fields)
        if active_model and active_ids:
            res['line_ids'] = []
            for rec in self.env[active_model].browse(active_ids):
                xml_id = rec.get_external_id().get(rec.id)
                res['line_ids'] += [(0, 0, {
                    'name': '%s (%s)' % (rec.display_name, xml_id) if xml_id
                    else rec.display_name,
                    'res_id': rec.id,
                    'xml_id': xml_id,
                    'attribute_ids': [
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
        active_model = self.env.context.get('active_model')
        self.ensure_one()
        if not self.line_ids or len(self.line_ids) <= 1:
            raise UserError(_(
                "Please select at least two records"
            ))

        try:
            to_delete = self.line_ids - self.line_id
            openupgrade_merge_records.merge_records(
                env=self.env,
                model_name=active_model,
                record_ids=to_delete.mapped('res_id.id'),
                target_record_id=self.line_id.res_id.id,
            )
        except Exception as error:
            raise UserError(_(
                "The records were not merge due to the next error: %s" %
                error))
        return True

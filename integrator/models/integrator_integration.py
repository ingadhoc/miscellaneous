from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tools import safe_eval
import dateutil
import datetime
import time
import pytz
import logging
import html
from lxml.html import fromstring
import html2text
from dateutil.relativedelta import relativedelta
import random
from odoo.netsvc import ColoredFormatter, RESET_SEQ, COLOR_SEQ, COLOR_PATTERN
import psycopg2


_logger = logging.getLogger(__name__)

MAX_RETRIES = 5


class IntegratorIntegration(models.Model):

    _name = 'integrator.integration'
    _inherit = ['mail.composer.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Integrator Integration'
    _mailing_enabled = True

    name = fields.Char(required=True, tracking=True, store=True, compute='_compute_name', default=lambda self: _('New'))
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed')],
                             copy=False, default='draft', required=True,
                             tracking=True)
    cron_id = fields.Many2one('ir.cron', 'Cron Task',
                              ondelete='restrict', copy=False)
    last_sync_start = fields.Datetime(
        help='Campo auxiliar utilizado para almacenar el momento el en cual inicia la sincro para que, si todo termina'
        ' bien, sea esta fecha la que se setea como ultima fecha de sincron (para no perder cosas que se hayan '
        'actualizado entre el momento de incio de ejecución de y fin, y tmb por el procesamiento en baches)')
    last_cron_execution = fields.Datetime(string="Last Execution")
    cron_nextcall = fields.Datetime(related='cron_id.nextcall', string="Next Call Execution")

    # Odoo2odoo Specific Fields
    odoo_db2 = fields.Many2one(
        "integrator.account", string="Remote Db",
        required=True,
        states={'confirmed': [('readonly', True)]},
        tracking=True,
        domain="[('state', '!=', 'draft')]",)
    script_line_ids = fields.One2many(
        "integrator.integration.script_line", "integration_id",
        string="Scripts",
        copy=True, context={'active_test': False})
    error_count = fields.Integer()
    active = fields.Boolean("Active", default=True)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # res._create_sequence()
        res._create_cron()
        return res

    @api.depends('odoo_db2', 'odoo_db2.name')
    def _compute_name(self):
        for rec in self:
            rec.name = _("%s ~ %s") % (self.env.cr.dbname, rec.odoo_db2.name)

    def write(self, vals):
        for rec in self:
            if 'active' in vals and not vals['active'] and rec.state != 'draft':
                raise UserError(_("You cannot archive integrations that are currently active. First stop the active integration so you can archive it."))
            # if 'active' in vals and rec.state == 'draft':
            #     logs = rec.env["integrator.integration.logging"].with_context({'active_test': False}).search([('integration_id', '=', rec.id)])
            #     if vals['active']:
            #         for log in logs:
            #             log.action_unarchive()
            #     else:
            #         for log in logs:
            #             log.action_archive()
        res = super().write(vals)
        return res

    def unlink(self):
        """ Deletes the integration, then the associated cron task and sequence.
        """
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_('You cannot delete integrations that are currently active. First stop the active integration so you can delete it.'))

        # # Unlink logs
        # self.env["integrator.integration.logging"].search([('integration_id', 'in', self.ids)]).unlink()

        # Unlink sequence
        # self.env['ir.sequence'].sudo().search([('code', 'in', ["integration.sync.%s" % id for id in self.ids])]).unlink()

        cron_ids = self.cron_id.ids

        result = super().unlink()

        # Unlink asociated crons
        self.env["ir.cron"].sudo().browse(cron_ids).unlink()

        return result

    def _create_cron(self, interval=30):
        """ Create a cron task associated to the given records without one
        """
        for rec in self:
            if not rec.cron_id:
                # Create a specific cron task for this integration
                _logger.info(
                    "Creating Cron Task for Integration #{}".format(self.id))
                code = "model.browse({})._cron_sync()".format(rec.id)
                dict_data = {
                    "name": "Integrator Sync {}".format(rec.id),
                    "active": True,
                    "code": code,
                    "user_id": self.env.ref("base.user_root").id,
                    "model_id": self.env.ref("integrator.model_integrator_integration").id,
                    "interval_number": interval,
                    "interval_type": "minutes",
                    "numbercall": -1,
                    "doall": False,
                    "nextcall": (datetime.datetime.now() + datetime.timedelta(
                        minutes=interval)).strftime('%Y-%m-%d %H:%M:%S'),
                    "state": "code",
                    "priority": 1000,
                }
                cron = self.env["ir.cron"].sudo().with_user(SUPERUSER_ID).create(dict_data)

                # Link them together
                rec.write({"cron_id": cron.id})
        return True

    def _cron_sync(self):
        return self.with_context(is_cron=True).sync()

    def _is_cron_running(self, cron_id):
        """ With this query we check if a cron is running.
            The code is taken from the method _try_lock from ir_cron model.
            We don't call the method directly to manage the exception.
        """
        try:
            self._cr.execute(f"""
                SELECT id
                FROM "{cron_id._table}"
                WHERE id = {cron_id.id}
                FOR NO KEY UPDATE NOWAIT
            """, log_exceptions=False)
        except psycopg2.OperationalError:
            self._cr.rollback()  # early rollback to allow translations to work for the user feedback
            raise UserError(_("This synchronization is currently being executed. "
                              "Please try again in a few minutes"))

    def back_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def test_and_confirm(self):
        res = self.test_connection()
        if res:
            return res
        self.write({'state': 'confirmed'})
        self.script_line_ids.write({'state': 'pending', 'next_offset': False})
        self.last_cron_execution = datetime.datetime.now()

    def sync(self):
        """ Sync for Odoo Integrations.
        Corremos un script en cada corrida de cron. Cuando todos se corrieron seteamos fecha de ultima corrida
        """
        self.ensure_one()
        if 'is_cron' not in self.env.context:
            self._is_cron_running(self.cron_id)

        if not self.state == 'confirmed':
            return

        _logger.info("Syncing Odoo Integration: Integration '%s'", self.name)

        jobs = self.script_line_ids.filtered('active').sorted('sequence')
        # si todo estan en pending estamos empezando una nueva corrida y los ponemos en cola
        if all(j.state == 'pending' for j in jobs):
            _logger.info("New sync execution, enqueuing tasks, integration '%s'", self.name)
            jobs.write({'state': 'enqueued'})
            self.last_sync_start = datetime.datetime.now()
            next_job = jobs[0]
        else:
            next_job = jobs.filtered(lambda j: j.state == 'started') or jobs.filtered(
                lambda j: j.state == 'enqueued')
            if not next_job:
                raise ValidationError(_('Error de programación, no hay proximo script para correr'))
            next_job = next_job[0]

        # corremos el proximo script
        self.odoo_run_job(next_job)

        # si todos se terminaron reseteamos estado 'pending' para nueva corrida y actualizamos fecha de ejecucion
        if all(j.state == 'done' for j in jobs):
            jobs.write({'state': 'pending'})
            _logger.info('Finish sync execution, last cron execution to %s', self.last_sync_start)
            self.last_cron_execution = self.last_sync_start
        elif self._context.get('cron_id'):
            self.env['ir.cron'].browse(self._context.get('cron_id'))._trigger()




        # TODO: post error Odumbo channel
        # Post errors
        # errors = result.get('error')

        # if errors:
        #     template = self.env.ref("integrator.integrator_logging_error_email_template")
        #     if template:
        #         template.send_mail(self.id, force_send=True)

    def action_reset_last_sync(self):
        """ Resets last sync date to allow sync everything again
        """
        self.last_cron_execution = False
        self.script_line_ids.write({'state': 'pending', 'next_offset': False})

    def test_connection(self):
        """ Test for Odoo Integrations.
        """
        self.ensure_one()
        user_call = True
        if 'is_cron' in self.env.context:
            user_call = False

        if not self.script_line_ids.filtered('active'):
            _logger.error("Integration %s. No active scripts found", self.id)
            if user_call:
                raise UserError(
                    "No hay scripts activos para la integración %s" % self.id)

        try:
            assert self.odoo_db2
            assert self.script_line_ids
        except Exception:
            _logger.error(
                "Integration {}: A required field is missing".format(self.id))
            if user_call:
                raise UserError("A required field is missing. Please verify.")

    def odoo_run_job(self, job):
        """ Run a single job """
        def sync_model(
                target_db, model_name, common_fields=[],
                boolean_fields=[], m2o_fields=[], m2m_fields=[], domain=[],
                sort="id", offset=0, limit=None, target_model_name=None):
            """ Helper method for allowing users to synchronize a model
            across two different Odoo clients.
            """

            def get_external_id(model_name, rec_id):
                """ Builds an external ID out of a model name and an ID.
                """
                return "__odumbo__.{}_{}".format(
                    model_name.replace(".", "_"), rec_id)

            start_time = datetime.datetime.now()
            _logger.debug("[sync_model] Synchronizing model '{}' with limit %s and offest %s".format(model_name, limit, offset))

            # Remove dots from model name
            norm_name = model_name.replace(".", "_")

            # Performs a SEARCH operation
            records = self.env[model_name].search(domain, order=sort, offset=offset, limit=limit)
            if len(records) == 0:
                _logger.info("[sync_model] No records were found in model %s meeting the given criteria", model_name)
                return
            _logger.info(
                "[sync_model] Syncing %s records for model %s (limit %s, offset %s)",
                len(records), model_name, limit, offset)

            #####
            # Create XML ids for odumbo for any record that has sane XML id on target db and source db (for eg. uoms)
            # but only for XML ids created by modules (not __import__ or __export__)
            #####

            # Obtain all automatic XML ids (not imported, exported or nulls)
            # Keep in mind many XML ids may point to the same record
            search_fields = ["complete_name", "module", "res_id", "name"]
            # TODO: se deber agregar sudo() para ir.model.data ??
            moddata_read = self.env["ir.model.data"].search_read([
                ("res_id", "in", records.ids),
                ("module", "not in", ["__import__", "__export__"]),
                ("model", "=", model_name)], search_fields)

            # We can't search by complete_name since it's a computed field.
            # If it wasn't, we would just do a recs.mapped("complente_name")
            # and search for these recs in the target DB
            if moddata_read:
                _logger.debug("Found {} records with existing XML ID".format(len(moddata_read)))
                # Fields we need to bring
                # Read necessary data from source DB
                _logger.debug("moddata_read: {}".format(moddata_read))

                # Now build a dict keyed by the complete_name
                moddata_dict = {}
                for item in moddata_read:
                    moddata_dict[item["complete_name"]] = item

                _logger.debug("moddata_dict: {}".format(moddata_dict))

                # Now we search for all these records that match our model,
                # all names, and all modules
                # TODO: se deber agregar sudo() para ir.model.data ??
                target_read = target_db.env["ir.model.data"].search_read([
                    ("module", "in", list(set([item["module"] for item in moddata_read]))),
                    ("name", "in", [item["name"] for item in moddata_read]),
                    ("model", "=", target_model_name or model_name)], search_fields)

                _logger.debug("taget_read: {}".format(target_read))

                # Prepare export data
                data = []
                for tr in target_read:
                    # If remote key exists in source database
                    if tr["complete_name"] in moddata_dict:
                        # Create a odumbo xmlid
                        name = "{}_{}".format(
                            norm_name,
                            moddata_dict[tr["complete_name"]]["res_id"])
                        module = "__odumbo__"
                        res_id = tr["res_id"]
                        data.append([name, target_model_name or model_name, module, res_id])

                _logger.debug("data: {}".format(data))

                # TODO ver de mejorar, actualmente esto nos está dando error en futuras iteraciones pero
                # no lo devolvemos, baicamente porque esto lo importamos sin external id y queremos importar external ids
                # de nuevo y ya existen. Tal vez habria que aprovechar a revisar toda esta lociga, tal vez usar
                # export_data? y mapear por name o por ese modulo de oca que permite definir otros criterios?
                if data:
                    # TODO: se deber agregar sudo() para ir.model.data ??
                    outcome = target_db.env["ir.model.data"].load(
                        ["name", "model", "module", "res_id"], data)

                    _logger.debug(outcome)
            #####
            # Finish creating XML ids for modules data
            #####

            # Perform READ operation a single time
            _logger.debug("[sync_model] Reading remote data for model %s", model_name)
            all_fields = common_fields + boolean_fields + m2o_fields + m2m_fields
            items = records.read(all_fields)

            _logger.debug("[sync_model] Adapting data previous to import for model %s", model_name)
            # Create a mapping between provided fields and converted fields
            fields_map = dict()
            for field in all_fields:
                if field in m2o_fields or field in m2m_fields:
                    fields_map[field] = field + "/id"
                else:
                    fields_map[field] = field

            # Collect all values for loading in a single operation
            values = list()

            for item in items:
                # Convert to string boolean fields (So that load don't fail because we search_read and load expects
                # different kind of data)
                for boolean_field in boolean_fields or []:
                    if item[boolean_field]:
                        item[boolean_field] = str(item[boolean_field])

                # Generate XML ids for M2O Fields
                for m2o_field in m2o_fields or []:
                    if item[m2o_field]:
                        rec_id = item[m2o_field].id
                        # esta operacion no tiene ejecuta ninguna ninguna llamada rpc, lo resuelve localmente odooly
                        rel_model_name = item[m2o_field]._model._name
                        item[m2o_field] = get_external_id(rel_model_name, rec_id)
                    else:
                        item[m2o_field] = False

                # Generate XML ids for M2M Fields
                for m2m_field in m2m_fields or []:
                    if item[m2m_field]:
                        rec_ids = item[m2m_field]
                        rel_model_name = item[m2m_field]._model._name
                        item[m2m_field] = ','.join([get_external_id(rel_model_name, rec_id) for rec_id in rec_ids.ids])
                    else:
                        item[m2m_field] = False

                item["id"] = get_external_id(model_name, item["id"])

                # List comprehension will create a list with "sorted" values
                result = [item[field] for field in all_fields]
                values.append(result)

            # Prevent templates from generating a product by themselves
            with_context = dict()
            if model_name == 'product.template':
                # YES, True means False
                with_context["create_product_product"] = True
            with_context["tracking_disable"] = True
            # key that can be used on custom modules to disable constrains or change any behaviour that
            # could help to speed up process
            with_context["odumbo_sync"] = True
            # for compatibility with new v13 bypass
            with_context["bypass_base_automation"] = True

            _logger.debug("[sync_model] Loading records on target db for model %s", model_name)
            outcome = target_db.env[target_model_name or model_name].with_context(
                **with_context).load(
                    [fields_map[field] for field in all_fields], values)

            if outcome.get('messages'):
                for count, msg in enumerate(outcome['messages']):
                    record = msg['record']
                    try:
                        record_id = values[record][all_fields.index('id')]
                        errors.append('[Error %s] %s: %s.' % (count + 1, record_id, msg['message']))
                    except ValueError:
                        errors.append('[Error %s] line %s: "%s".\n' % (count + 1, record, msg['message']))

                errors.append('Error completo: %s' % (outcome.get('messages')))
            elif not outcome.get('ids'):
                errors.append('Error no atrapado al sincronizar "%s". No recibimos ni messages ni ids. Recibimos %s' % (
                    model_name, outcome))
            else:
                ok.append('Sincronizados "%s" elementos en "%s"' % (model_name, len(outcome.get('ids'))))
                _logger.info(
                    "[sync_model] Finish syncking records for model %s on %s hours", model_name,
                    str((datetime.datetime.now() - start_time)))
            _logger.info(
                "[sync_model] Finish WITH ERRORS syncking records for model %s on %s hours", model_name,
                str((datetime.datetime.now() - start_time)))

        self.ensure_one()
        errors = []
        ok = []

        _logger.info("Running job: '%s'", job.script_id.name)
        job_start = datetime.datetime.now()
        if job.state != 'started':
            job.state = 'started'

        # The following libraries and variables
        # will be available for any job.
        locals_dict = {
            "db2": self.odoo_db2._odoo_get_client(),
            "last_cron_execution": self.last_cron_execution,
            "last_sync_start": self.last_sync_start,
            "offset": job.next_offset,
            "Warning": UserError,
            "context": dict(self._context),
            "datetime": safe_eval.datetime,
            "dateutil": safe_eval.dateutil,
            "timezone": safe_eval.pytz,
            "time": safe_eval.time,
            "errors": errors,
            "ok": ok,
            "sync_model": sync_model,
        }

        try:
            safe_eval.safe_eval(job.script_id.code, locals_dict, mode="exec", nocopy=True)
        except Exception as e:
            errors.append(repr(e))

        if errors:
            # si hay errores ponemos mensaje y pasamos a borrador
            if 'is_cron' not in self.env.context:
                raise ValidationError('Error al sincronizar, esto es lo que obtuvimos:\n%s' % '\n\n'.join(errors))
            elif self.error_count < MAX_RETRIES:
                self.error_count += 1
                _logger.warning('Error (%s try) found while running job "%s" (integration %s)',
                                self.error_count, job.script_id.name, self.name)
            else:
                self.sudo().message_post(
                    subtype_id=self.env.ref('integrator.mt_error').id,
                    body='Error al sincroniazar, se vuelve a borrador la integracion. Esto es lo que obtuvimos: %s' % (
                        '<br/>'.join(errors)))
                job.state = 'failed'
                _logger.warning(
                    'Error (last try) found while running job "%s" (integration %s), check chatter for more info',
                    job.script_id.name, self.name)
                self.back_to_draft()
            return
        elif ok:
            # si hay mensajes de ok quiere decir que algo se sincronizo, si hay limite cambiamos limite y seguimos para
            # que lo tome proxima corrida
            message = """
            <p>Job run '{}' finish sucessfully on {}</p>
            <p>{}</p>
            """.format(job.script_id.name, str(datetime.datetime.now() - job_start), html.escape(str(ok)))
            self.sudo().message_post(body=message)
            self.error_count = 0

            limit = locals_dict.get('limit', False)
            if limit:
                next_offset = job.next_offset + limit
                _logger.info('Setting new offset = %s for next iteration', next_offset)
                job.next_offset = next_offset
                return
        # si no hay limite o no no hay resultados, parcamos realizada y reseteamos offset
        _logger.info('Finish sync execution, cleaning offset and setting job done')
        job.write({'state': 'done', 'next_offset': False})

    def action_add_odoo_account(self):
        wiz_vals = {
            'partner_id': self.partner_id.id,
            'integration_id': self.id,
        }
        wiz = self.env['integrator.account.wizard'].create(wiz_vals)
        return {
            'name': 'New Odoo Account',
            'view_mode': 'form',
            'res_model': 'integrator.account.wizard',
            'res_id': wiz.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

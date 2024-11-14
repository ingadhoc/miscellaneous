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
    # sync_number = fields.Char('Synchronization Number', copy=False, index=True, default='NaN')
    # version = fields.Selection([
    #     ('stable', 'Stable'),
    #     ('development', 'Development')],
    #     tracking=True, required=True, default='stable', states={'confirmed': [('readonly', True)]})
    # integration_type_id = fields.Many2one('integration.type', required=True)
    # is_odoo_odoo = fields.Boolean(compute='_compute_is_odoo_odoo', store=True)
    # partner_id = fields.Many2one(
    #     'res.partner', string='Partner', tracking=True,
    #     ondelete='restrict', default=lambda self: self.env.user.partner_id)
    # commercial_partner_id = fields.Many2one(
    #     'res.partner', string='Commercial Entity', compute_sudo=True,
    #     related='partner_id.commercial_partner_id', store=True, readonly=True,)
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

    # odoo_db1 = fields.Many2one(
    #     "integrator.account", string="Odoo Database 1",
    #     states={'confirmed': [('readonly', True)]},
    #     tracking=True,
    #     domain="[('account_type', '=', 'odoo'), ('commercial_partner_id', '=', commercial_partner_id), ('state', '!=', 'draft')]",
    #     context={'default_account_type': 'odoo'})
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

    # @api.depends('integration_type_id')
    # def _compute_is_odoo_odoo(self):
    #     for rec in self:
    #         rec.is_odoo_odoo = rec.integration_type_id.application == 'odoo'

    # def _get_sync(self, sandbox_mode=False, context={}):
    #     if self.odoo_db2:
    #         odoo2 = self.odoo_db2._odoo_get_client()
    #     ctx = self._get_sync_context()
    #     ctx.update(context)
    #     return Sync(odoo, odoo2, sandbox_mode, ctx) if self.version == 'stable' else SyncDev(odoo, odoo2, sandbox_mode, ctx)

    # def _get_sync_context(self):
    #     self.ensure_one()
    #     fields = [
    #         'id',
    #         'sync_number',
    #     ]
    #     ctx = self.read(fields)[0]
    #     ctx.update(user_call='is_cron' not in self.env.context)
    #     return ctx

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

    # def _create_sequence(self):
    #     for rec in self:
    #         if not self.env['ir.sequence'].sudo().search([('code', '=', 'integration.sync.%s' % rec.id)], limit=1):
    #             self.env['ir.sequence'].sudo().create({
    #                 'name': "Integrator Sync %s" % rec.id,
    #                 'code': "integration.sync.%s" % rec.id,
    #                 'prefix': '#',
    #                 'padding': 6,
    #             })
    #     return True

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

    # @api.model
    # def _gc_integration_logs(self):
    #     Logs = self.env['integrator.integration.logging']
    #     logs_to_archive = Logs
    #     logs_to_remove = Logs

    #     logs_to_archive |= Logs.search([
    #         ('create_date', '<', fields.Datetime.now() - relativedelta(days=15)),
    #     ])
    #     logs_to_remove |= Logs.with_context({'active_test': False}).search([
    #         ('create_date', '<', fields.Datetime.now() - relativedelta(days=30)),
    #     ])
    #     logs_to_archive.action_archive()
    #     logs_to_remove.unlink()

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

    # def test(self):
    #     for rec in self:
    #         if hasattr(rec, '%s_test' % rec.integration_type_id.application):
    #             return getattr(rec, '%s_test' % rec.integration_type_id.application)()
    #         else:
    #             _logger.warning(
    #                 "Integration '%s' has no %s_test method!" %
    #                 (rec.name, rec.integration_type_id.application))

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

    # def _format_summary_sync_msg(self, result):
    #     if result['info'] or result['warning'] or result['error']:
    #         return _(
    #             """
    #             <h3>Synchronization {sync_number}</h3>
    #             <p>Summary of updated data:</p>
    #             <ul>
    #             <li>Info: <strong>{info}</strong></li>
    #             <li>Warnings: <strong>{warning}</strong></li>
    #             <li>Errors: <strong>{error}</strong></li>
    #             </ul>
    #             <p>Check all the log lines here <strong><a class="alert-link"
    #             " href="/web#action=integrator.action_integrator_integration_logging" role="button">View logs.</a>
    #             """).format(
    #                 sync_number=self.sync_number,
    #                 info=len(result['info']),
    #                 warnings=len(result['warning']),
    #                 errors=len(result['error']),
    #             )
    #     else:
    #         return _(
    #             """
    #             <h3>Synchronization {sync_number}</h3>
    #             <p>No changes were made on the synchronized accounts.</p>
    #             """).format(sync_number=self.sync_number)

    # def _log_sync_result(self, result):
    #     ''' Create integration logs from results.
    #         Expected format: {
    #             'info': [msg],
    #             'warning': [msg],
    #             'error': [msg],
    #             'metrics': {}
    #         }
    #     '''
    #     if 'metrics' in result:
    #         del(result['metrics'])
    #     # Create logs
    #     log_vals = []
    #     for type, messages in result.items():
    #         for msg in messages:
    #             log_vals.append({
    #                 'integration_id': self.id,
    #                 'sync_number': self.sync_number,
    #                 'log_type': type,
    #                 'message': msg,
    #             })
    #     self.env['integrator.integration.logging'].sudo().create(log_vals)
    #     # Create a summary of changes
        # message = self._format_summary_sync_msg(result)
        # self.sudo().message_post(subtype_id=self.env.ref('integrator.mt_log').id, body=message)

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

    # def _get_error_log_url(self):
    #     base_url = self.get_base_url()
    #     action = self.env.ref("integrator.action_integrator_integration_logging_errors")
    #     path = '/web#&action=%s&model=integrator.integration.logging&view_type=' % (action.id)
    #     return base_url + path

    # def test_synchronization(self):
    #     """ Mthod to be override by specifics integrations tests.
    #     Return an empty dict if no errors. Otherwise return a dict with errors
    #     """
    #     return dict()


# class IntegratorColoredFormatter(ColoredFormatter):
#     def format(self, record):
#         record.prefix = COLOR_PATTERN % (30 + record.color, 40, record.prefix)
#         return ColoredFormatter.format(self, record)


# class IntegrationType(models.Model):
#     _name = 'integration.type'
#     _description = 'Integration Type'

#     name = fields.Char()
#     application = fields.Selection([('odoo', 'Odoo')], required=True,)


# class Sync():
#     ''' Class that represents a generic synchronizations between two accounts '''

#     def __init__(self, odoo, odoo2=None, sandbox_mode=False, ctx={}):
#         self.odoo = odoo
#         if odoo2:
#             self.odoo2 = odoo2
#         self.sandbox_mode = sandbox_mode
#         self.ctx = ctx
#         self.result = {'info': [], 'warning': [], 'error': []}
#         # Logger
#         sync_logger = logging.getLogger(self.__class__.__name__)
#         myHandler = logging.StreamHandler()
#         # Change Odoo log format
#         format = '%(asctime)s %(pid)s %(levelname)s %(name)s:: %(prefix)s %(message)s'
#         myFormatter = IntegratorColoredFormatter(format)
#         myHandler.setFormatter(myFormatter)
#         sync_logger.handlers.clear()
#         sync_logger.addHandler(myHandler)
#         sync_logger.propagate = False
#         self.logger = logging.LoggerAdapter(sync_logger, extra={
#             'prefix': "[SANDBOX][Integration %s]" % ctx.get('id') if self.sandbox_mode else "[Integration %s]" % ctx.get('id'),
#             'color': random.randint(1, 7),
#         })

#     def _ensure_field(self, field_model, field_name):
#         if self.odoo.env[field_model]._fields.get(field_name):
#             return True
#         else:
#             if hasattr(self, '_create_field_%s' % field_name):
#                 return getattr(self, '_create_field_%s' % field_name)()
#             else:
#                 self.result['error'].append("Field %s no found in the model %s." % (field_name, field_model))


# class SyncDev(Sync):
#     ''' Class that represents a generic Dev synchronizations between two accounts '''

#     pass

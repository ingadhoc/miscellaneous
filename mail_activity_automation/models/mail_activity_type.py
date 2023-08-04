from odoo import models, fields, api


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    run_automatically = fields.Boolean(help="Si marca esta opción, llegada la fecha de vencimiento, se enviará la plantilla seleccionada y se marcará la actividad como realizado.")





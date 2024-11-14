# Copyright (c) 2007 Ferran Pegueroles <ferran@pegueroles.com>
# Copyright (c) 2009 Albert Cervera i Areny <albert@nan-tic.com>
# Copyright (C) 2011 Agile Business Group sagl (<http://www.agilebg.com>)
# Copyright (C) 2011 Domsense srl (<http://www.domsense.com>)
# Copyright (C) 2013-2014 Camptocamp (<http://www.camptocamp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def behaviour(self):
        # Agregamos esto para poder saltear restricciones de cups agregadas en este pr: https://github.com/OCA/report-print-send/pull/367
        # self = self.with_context(skip_printer_exception=True)
        result = super().with_context(skip_printer_exception=True).behaviour()
        return result

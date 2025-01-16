# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    employee_overtime = fields.Float(related='employee_id.total_overtime', groups='base.group_user,portal_holidays.group_portal_backend_holiday')

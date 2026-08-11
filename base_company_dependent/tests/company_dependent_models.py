##############################################################################
#
#    Copyright (C) 2024  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields, models


class CompanyDependentTester(models.Model):
    """Transient model registered only during the tests (added to the registry
    in setUpClass, rolled back by TransactionCase). Gives the suite a
    company_dependent Many2one so the protection can be tested without account."""

    _name = "company.dependent.tester"
    _description = "Company Dependent Tester (tests only)"

    name = fields.Char()
    partner_id = fields.Many2one("res.partner", company_dependent=True)
    partner_regular_id = fields.Many2one("res.partner")
    currency_id = fields.Many2one("res.currency", company_dependent=True)

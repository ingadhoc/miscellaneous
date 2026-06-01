##############################################################################
#
#    Copyright (C) 2026  ADHOC SA  (http://www.adhoc.com.ar)
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
{
    "name": "Account Reconcile Background",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "ADHOC SA",
    "website": "https://www.adhoc.com.ar",
    "license": "AGPL-3",
    "summary": "Process bank reconciliation in background for large payment batches",
    "depends": [
        "account_accountant_batch_payment",
        "base_bg",
    ],
    "data": [
        "data/ir_config_parameter_data.xml",
    ],
    "installable": True,
    "auto_install": False,
}

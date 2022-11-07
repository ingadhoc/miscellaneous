##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import wizards

from odoo.addons.base_report_to_printer import __manifest__ as manifest

manifest.pop('external_dependencies')

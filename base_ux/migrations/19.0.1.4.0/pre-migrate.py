from odoo.upgrade import util


def migrate(cr, version):
    util.remove_view(cr, "base_ux.view_partner_form_mobile")
    util.remove_view(cr, "base_ux.view_partner_tree_mobile")

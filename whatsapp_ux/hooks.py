##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################


def post_init_hook(env):
    """Provision the bulk send server action for templates that are already
    approved when the module is installed."""
    templates = env["whatsapp.template"].search([("status", "=", "approved")])
    templates._sync_bulk_send_action()

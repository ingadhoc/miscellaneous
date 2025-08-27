from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """
    Update field descriptions for dynamic messages to ensure consistency.
    Sets description to 'Dynamic Message {id}' format for all related fields.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    dynamic_messages = env["ir.model.dynamic_message"].search([])

    for msg in dynamic_messages:
        expected_description = f"Dynamic Message {msg.id}"
        field_to_update = None

        if msg.field_id:
            field_to_update = msg.field_id
        else:
            # search for orphaned field that should be linked to this message
            field_name = f"x_dynamic_message_{msg.id}"
            field_to_update = env["ir.model.fields"].search(
                [("model", "=", msg.model_id.model), ("name", "=", field_name)], limit=1
            )

        # update field description if needed
        if field_to_update and field_to_update.field_description != expected_description:
            field_to_update.write({"field_description": expected_description})

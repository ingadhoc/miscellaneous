##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""The fields that must not reach a client through the AI/API read path or the
export, declared in one place.

The value is a `has_groups` spec, so it reads like `groups=` on the field: the
groups that MAY read it, with `!` for the ones that may not. Unlike `groups=`,
it does not take the field away from the server, so the computes keep working.

A field whose module is not installed is not in `_fields`, and its entry does
nothing. Adding a field is a pull request to this file.
"""

FIELD_EDGE_SECURITY = {
    "product.product": {
        "standard_price": "!price_security.group_only_view_sale_price",
    },
    "product.template": {
        "standard_price": "!price_security.group_only_view_sale_price",
    },
}


def validate_rules(rules):
    """Fail at load time on an entry that is not in the format, so a typo in a
    pull request to this file does not become a field that silently stays open.
    Whether the model, the field and the groups exist is checked by the tests:
    here they are usually absent because their module is not installed."""
    if not isinstance(rules, dict):
        raise ValueError("FIELD_EDGE_SECURITY must map a model name to its fields")
    for model_name, fields in rules.items():
        if not isinstance(model_name, str) or "." not in model_name:
            raise ValueError("FIELD_EDGE_SECURITY: %r is not a model name" % (model_name,))
        if not isinstance(fields, dict) or not fields:
            raise ValueError("FIELD_EDGE_SECURITY[%r] must map a field name to a group spec" % (model_name,))
        for field_name, group_spec in fields.items():
            where = "FIELD_EDGE_SECURITY[%r][%r]" % (model_name, field_name)
            if not isinstance(field_name, str) or not field_name.isidentifier():
                raise ValueError("%s: %r is not a field name" % (where, field_name))
            if not isinstance(group_spec, str) or not group_spec.strip():
                raise ValueError("%s: the group spec is empty" % where)
            for token in group_spec.split(","):
                xml_id = token.strip().removeprefix("!")
                if xml_id.count(".") != 1 or not all(xml_id.split(".")):
                    raise ValueError("%s: %r is not a fully qualified group xml id" % (where, token))


validate_rules(FIELD_EDGE_SECURITY)

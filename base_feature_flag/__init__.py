import functools
import os

ENV_PREFIX = "SAAS_FEATURE_"
PARAM_PREFIX = "saas_feature."
TRUE_VALUES = ("1", "true", "yes")


def is_on(env, name):
    """Return whether the feature flag ``name`` is on.

    The environment variable ``SAAS_FEATURE_<NAME>`` wins over the system
    parameter ``saas_feature.<name>``. Plain functions (not model methods) so
    they work even in databases where this module is not installed.
    """
    value = os.environ.get(f"{ENV_PREFIX}{name.upper()}")
    if not value:
        value = env["ir.config_parameter"].sudo().get_param(f"{PARAM_PREFIX}{name}", "")
    return value.strip().lower() in TRUE_VALUES


def flag(name, variant):
    """Call method ``variant`` instead of the decorated one when ``name`` is on.

    The choice is made on every call, so each database follows its own flag.
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if is_on(self.env, name):
                return getattr(self, variant)(*args, **kwargs)
            return method(self, *args, **kwargs)

        return wrapper

    return decorator

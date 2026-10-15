Base Feature Flag
=================

Lets a method have a variant that is used only when a feature flag is on, without writing a proxy method for each case.

**Table of contents**

.. contents::
   :local:

Usage
=====

A flag named ``<name>`` is on when:

* the environment variable ``SAAS_FEATURE_<NAME>`` is ``1``, ``true`` or ``yes``, or
* that variable is not set and the system parameter ``saas_feature.<name>`` is ``1``, ``true`` or ``yes``.

The flag is checked on every call, so each database follows its own system parameter.

Decorator
---------

.. code-block:: python

    from odoo.addons.base_feature_flag import flag

    class AccountMove(models.Model):
        _inherit = "account.move"

        @flag("ws_v2", "_send_ws_v2")
        def send(self):
            ...  # current version

        def _send_ws_v2(self):
            ...  # new version

``@flag`` keeps the attributes set by the ``@api.*`` decorators. With decorators that wrap and cache the result, such as ``@ormcache``, ``@flag`` must go on top.

Plain check
-----------

.. code-block:: python

    from odoo.addons.base_feature_flag import is_on

    def send(self):
        if not is_on(self.env, "ws_v2"):
            return super().send()
        ...

Optional dependency
-------------------

A module can use the flag without adding ``base_feature_flag`` to its ``depends``. Where the module is not available, the current version always runs:

.. code-block:: python

    try:
        from odoo.addons.base_feature_flag import flag, is_on
    except ImportError:
        def flag(name, variant):
            return lambda fn: fn

        def is_on(env, name):
            return False

Credits
=======

Authors
-------

* ADHOC SA

Contributors
------------

* ADHOC SA Development Team

Maintainers
-----------

This module is maintained by ADHOC SA.

.. image:: https://www.adhoc.com.ar/logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

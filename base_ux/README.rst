.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======
Base UX
=======

Several Improvements:
    * New button to add/remove a window action as a contextual action in the windows source model.
    * If a partner is Actived/Archived will be tracked in its message log.
    * Be able to use re python library and odoo.tools.html2plaintext()function in server actions, ir.cron, base.automation, etc.
    * Make parent field on res.company invisible as it is useless now
    * Keep the activity's description when changing the activity type, regardless of the activity type's description, and change the activity user only if the activity type has a default user.
    * Make company_registry field on res.company invisible as it is useless now
    * Blank a sensitive field on the client read path (read, search_read, web_read) and refuse to export it, while the ORM goes on reading it for the business logic.


Installation
============

Only install the module.

Configuration
=============

There is nothing to configure, except for the list of fields that must not
reach a client, in ``models/field_edge_security.py``::

    FIELD_EDGE_SECURITY = {
        "product.product": {
            "standard_price": "!price_security.group_only_view_sale_price",
        },
    }

The value is a ``has_groups`` spec, so it reads like ``groups=`` on the field:
the groups that may read it, with ``!`` for the ones that may not. Unlike
``groups=``, it does not take the field away from the server, so the computes
and the valuation go on working.

A field whose module is not installed is simply not there and its entry does
nothing, so one list covers every base. Adding a field is a pull request to
that file.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/miscellaneous/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.

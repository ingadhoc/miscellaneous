.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========
First Steps
===========

 * Adds a "First Steps" section as the first block of General Settings, linking to a single panel that gathers the onboarding initial imports.
 * Shows each shortcut depending on the installed modules: Import Products (with ``product``), Import Customers / Import Vendors (with ``account_balance_import``, classified through the rank), Import Contacts (otherwise), and the Accounting setup guide (with ``account_balance_import``).
 * Recommends always using a fresh, clean template downloaded from the system to avoid errors carried by reused spreadsheets.
 * Makes import errors less disruptive: a single badly-formatted number or date no longer cancels the whole import. Instead of raising on the first bad cell (which hides every other error and the offending row number), the value is deferred to the per-record ORM converter, which reports it **with its row number and expected-format hint**, accumulated together with every other field/record error in one pass.

Technical notes
===============

 * ``base_import.import._parse_float_from_data`` / ``_parse_date_from_data`` are overridden to stop aborting the import on the first unparseable value (they used to ``raise ImportValidationError``). Only genuinely unexpected (non-``ValueError``) date failures are still raised.

Installation
============

Only install the module.

Configuration
=============

This module does not need any configuration.

Usage
=====

Go to "Settings > General Settings" and, in the "First Steps" block, click "Open First Steps". The panel shows the available import shortcuts according to the installed modules.

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

.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.inc

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================
Export Background
=================

Automatically exports large datasets (>500 records) in background to avoid timeouts.

Installation
============

Install the module and its dependency: ``base_bg``

Configuration
=============

Optional: Configure the record threshold in **Settings > Technical > System Parameters**:

* Key: ``export_bg.record_threshold``
* Default: ``500``

Usage
=====

1. Go to any list view and select records to export
2. Click **Export** and choose your format (CSV or XLSX)
3. If records exceed the threshold:
   - You'll receive a notification: "Export sent to background"
   - You'll receive a message with download link when ready

For exports under the threshold, it works as normal (instant download).

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.dev-adhoc.com/

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

To contribute to this module, please visit https://www.adhoc.inc.

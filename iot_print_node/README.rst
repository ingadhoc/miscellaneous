.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
IoT Print Node Printing
=========================

This module integrates PrintNode cloud printing service with Odoo's printers, adding PrintNode as a printer type, so you can print documents directly to PrintNode printers without requiring an IoT Box.

Installation
============

Before installing this module, you need to:

1. Have a PrintNode account (https://www.printnode.com/)
2. Get your PrintNode API Key from your PrintNode account settings

Configuration
=============

To configure this module:

1. Activate the developer mode and go to **Settings > Technical > Reporting > PrintNode > Add PrintNode**
2. Enter a name for your PrintNode account
3. Enter your PrintNode API Key
4. Click **Add** to create the PrintNode account and automatically import your printers
5. Use **Update printnode printers** on the account to sync them again with Odoo
6. Link each printer to the reports it has to print, from **PrintNode > Printers** or from the report

Usage
=====

Once configured:

* Your PrintNode printers will appear in the printers list, with the PrintNode type
* You can print reports directly to PrintNode printers from any Odoo document, choosing the printer when printing
* The system will automatically send print jobs to PrintNode cloud service
* You'll receive a notification when a print job is successfully sent

Features
========

* **Cloud-based printing**: Print without an IoT Box
* **Automatic printer sync**: Printers are automatically imported from your PrintNode account
* **Easy setup**: Simple wizard to add PrintNode credentials
* **Real-time notifications**: Get notified when print jobs are sent
* **Multiple printer support**: Manage multiple PrintNode accounts and printers from a single Odoo instance

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

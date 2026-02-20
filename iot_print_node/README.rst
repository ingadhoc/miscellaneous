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

This module integrates PrintNode cloud printing service with Odoo's IoT functionality, allowing you to print documents directly to PrintNode printers without requiring a physical IoT Box.

Installation
============

Before installing this module, you need to:

1. Have a PrintNode account (https://www.printnode.com/)
2. Get your PrintNode API Key from your PrintNode account settings

Configuration
=============

To configure this module:

1. Go to **IoT > Add PrintNode**
2. Enter a name for your PrintNode IoT Box
3. Enter your PrintNode API Key
4. Click **Add** to create the IoT Box and automatically import your printers
5. Your PrintNode printers will be automatically synced with Odoo

Usage
=====

Once configured:

* Your PrintNode printers will appear in the IoT devices list
* You can print reports directly to PrintNode printers from any Odoo document
* The system will automatically send print jobs to PrintNode cloud service
* You'll receive a notification when a print job is successfully sent

Features
========

* **Cloud-based printing**: Print without a physical IoT Box
* **Automatic printer sync**: Printers are automatically imported from your PrintNode account
* **Easy setup**: Simple wizard to add PrintNode credentials
* **Real-time notifications**: Get notified when print jobs are sent
* **Multiple printer support**: Manage multiple PrintNode printers from a single Odoo instance

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

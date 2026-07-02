.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

===========
WhatsApp UX
===========

Automatically provisions a one-click bulk send server action for every approved
WhatsApp template, on any model:

    * When a WhatsApp template becomes approved (and has *Bulk Send Action* enabled), a native "Send WhatsApp" server action is created on that template's model list view.
    * The action shows up in the *Action* menu of the model's list; sending is handled by the native WhatsApp batch + cron queue (no custom send logic).
    * The action is removed automatically when the template is unapproved, opted out, or deleted.

This generalises the native per-template *Allow Multi* button: instead of an
opt-in composer wizard created by hand, every approved template gets a
versioned, upgrade-safe, one-click bulk send action. For example, with the
``whatsapp_account`` module installed and its *Invoice* template approved,
"Send by WhatsApp: Invoice" shows up in the invoices list Action menu with no
manual UI setup.


Installation
============

Only install the module.

Configuration
=============

There is nothing to configure. Uncheck *Bulk Send Action* on a WhatsApp
template to opt it out of the automatic action.

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

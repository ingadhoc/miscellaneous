.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========
Portal UX
=========

Usability improvements for the portal access wizard.

* Adds a **"Grant Access to All"** button to the portal access wizard
  (``portal.wizard``), granting portal access to every contact loaded in the
  wizard in a single pass.
* Applies only to contacts with a valid email (``email_state == 'ok'``) that
  don't already have portal access and are not internal users
  (``is_portal`` / ``is_internal``); the rest are skipped without raising an
  error.
* Reuses the native per-row logic (``action_grant_access``) of
  ``portal.wizard.user``, so any override of that method added by other
  modules keeps applying.


Installation
============

Only install the module.

Configuration
=============

There is nothing to configure.

Usage
=====

#. Go to **Contacts**, select one or more contacts and run the **"Grant
   portal access"** action (``portal.wizard``).
#. In the wizard, click **"Grant Access to All"**.
#. Every listed contact with a valid, unused email gets portal access in a
   single operation.

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

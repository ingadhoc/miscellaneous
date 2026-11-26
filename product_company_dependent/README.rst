.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

============================
Product Company Dependent UX
============================

Adds the per-company values dialog of ``base_company_dependent`` to the
product cost (``standard_price``) on the product form.

* With a single variant, the dialog reads and writes the variant cost, so it
  shows which companies have their own value and *Reset* goes back to the
  default.
* With several variants, standard Odoo hides the cost on the template and only
  saves it on each variant, so the dialog refuses to work on the template.

Installation
============

The module installs automatically wherever ``base_company_dependent`` and
``product`` are installed.

Configuration
=============

Nothing to configure.

Usage
=====

Open a product and press the building icon next to *Cost*.

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

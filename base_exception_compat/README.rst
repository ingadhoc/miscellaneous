.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=====================
Base Exception Compat
=====================

Keeps the exception flow that `base_exception` had before OCA/server-tools#3590,
where `detect_exceptions()` writes in the ongoing transaction and returns the
rules instead of writing through a second cursor and raising.

The upstream mechanism opens a second database connection to store the
exceptions. That connection writes the same rows the ongoing transaction is
about to write, so the operation either fails with a serialization error or
blocks until the worker is killed. It also turns the exception into an error
for any caller outside the backend web client (portal, e-commerce, API, cron),
because the handler that translates it into a popup is only registered in
`web.assets_backend`.

The replacement belongs here and not in a module of a specific application:
`detect_exceptions()` is defined on `base.exception.method`, the abstract model
every exception module inherits from, so `sale_exception`, `stock_exception`
and any other one are all affected. Keeping it in `sale_exception_compat` left
stock covered only as long as a sale module happened to be installed, with
nothing declaring that dependency.

Installation
============

To install this module, you need to:

#. Only need to install the module. It is auto installed with `base_exception`.

Configuration
=============

To configure this module, you need to:

#. Nothing to configure.

Usage
=====

To use this module, you need to:

#. Confirm or validate a record that matches an exception rule: the exception
   popup shows up instead of an error.

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

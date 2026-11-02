.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

====================
Field Edge Security
====================

Keeps a field out of every path a client can read it from, without taking it
away from the ORM.

Hiding a field in the view is not security: the value still comes back through
RPC, the export dialog, a pivot measure, Ask AI or any other client of the
ORM. The usual answer, ``groups=`` on the field, closes it for the server too
(``Field.__get__`` checks it since 19.0), so the business logic that reads the
field with the user stops working.

This module closes only the edge. A field declared with ``edge_groups`` is:

* dropped from ``fields_get``, so a client does not discover it;
* empty in ``_read_format``, which covers ``read``, ``search_read`` and
  ``web_read``, including the fields an embedded x2many brings along;
* refused in ``export_data``;
* refused in the domain and the order of ``_search``;
* refused in the domain, the ``having``, the groupby, the aggregates and the
  order of ``_read_group``;
* removed from the view arch, because the web client raises "field is
  undefined" for a ``<field>`` node the view does not return.

The ORM keeps reading the field for itself, so computes, valuations and the
rest of the business logic go on working.

Declaring a field
=================

Next to the field, like ``groups=``::

    class ProductTemplate(models.Model):
        _inherit = "product.template"

        standard_price = fields.Float(
            edge_groups="!price_security.group_only_view_sale_price")

The value is a ``has_groups`` spec: the groups that may read it, with ``!``
for the ones that may not.

A field that derives from a protected one has to be declared too. The module
closes read paths, it does not follow a value: with the cost hidden, a margin
that is ``price - cost`` still gives the cost away, so ``margin`` carries its
own ``edge_groups``.

What this does not cover
========================

* ``env.su``. Code running as superuser reads everything, by design.
* A different user. A field restricted for one user is readable by another one
  who is allowed, including a service account.
* Anything outside the ORM read paths listed above, such as a report that
  renders the value server-side.

Installation
============

Only install the module.

Configuration
=============

There is nothing to configure. Fields are declared in code.

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

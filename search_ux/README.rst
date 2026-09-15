.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========
Search UX
=========

Adds a place to store the aliases people actually search by, and a configuration
point to add fields to the search, without changing Odoo's native behaviour when
the search already works.

Out of the box:

* A "Search Keywords" field on products and contacts (internal: it is not
  printed nor published), already included in the search of those two models.
* Nothing else enabled. Everything else is opt-in.

The extended search only runs when the native search did not fill the suggestion
list, and always as a single query.

Where it searches
=================

Both search surfaces of the backend find the same records:

* The **autocomplete** when picking the record on a document (sales order line,
  purchase order line, Customer field): the native cascade runs first (internal
  reference and barcode exact, reference and name partial, code between
  brackets, vendor code) and the extended search only completes the suggestion
  list if it was not filled.
* The **Search...** box of the list and kanban views. On products the search
  views are extended with the technical field ``search_extended``, which
  resolves the same criteria; on contacts nothing has to be extended, their
  search box already goes through ``display_name``.

Installation
============

Only install the module.

Configuration
=============

Settings > Extended Search, per model:

* **Fields to Include**: model fields, Studio fields and forward paths
  (``product_tmpl_id.my_field``).
* **Related Sources** (products): lots/serials, vendor code, packaging barcodes.
* **Minimum Characters** before the extended search is triggered (default 3).
* Archive the configuration to turn it off completely.

It rejects, on save: HTML fields, binary/attachment fields, non stored fields,
wrong paths, group restricted fields and more than 5 fields per model
(``search_ux.max_fields``).

Usage
=====

Load the aliases in "Search Keywords" and search by them from any many2one
(sales order lines, invoices, etc) or from the Search... box of the Products
and Contacts lists.

Rollout note
============

What to tell the customer before installing:

* The day it is installed **the field is empty and nothing new is found**. The
  aliases are loaded by the customer: the module does not guess them and does
  not migrate what is today in internal notes or tags.
* To load many at once, export Products or Contacts to a spreadsheet, fill the
  "Search Keywords" column and import it back. One record per row, the aliases
  separated by spaces.
* Accents and case follow whatever ``ilike`` does on the deployment: with the
  ``unaccent`` option disabled, "clapen" does not find "Clappen". It is a
  deployment setting, not something the module decides.

Customization
=============

To search by something that is not a field of the model (an own model, a
history, business logic), inherit the single extension point from a customer
module::

    class ProductProduct(models.Model):
        _inherit = "product.product"

        def _get_extra_search_domains(self, term):
            domains = super()._get_extra_search_domains(term)
            domains.append(Domain("id", "in",
                self.env["my.model"]._search([("code", "ilike", term)])
                    .subselect("product_id")))
            return domains

Known issues / Roadmap
======================

* It does not fix typos, does not reserve the lot when the product is found by
  serial number and does not search inside HTML descriptions. All three are
  explicit decisions.
* The configuration is per model: what is configured on ``product.template``
  does not apply to ``product.product`` and the other way around. Sales order
  lines search variants, the Products list searches templates, so a customer
  that configures extra fields usually wants both. The keywords field, which is
  what works out of the box, is consistent on both.
* Related sources (lots, vendor code, packaging barcodes) are skipped for users
  without read access to those models, instead of raising: a salesperson
  without inventory rights simply does not search by lot.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/ingadhoc/miscellaneous/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Credits
=======

|company_logo|

|company|

This module is maintained by the |company|.

To contribute to this module, please visit https://github.com/ingadhoc.

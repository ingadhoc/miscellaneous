.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============
Portal Backend
==============

This module creates a new user type "Portal Backend" that grants access to the Odoo backend. However, users with this group won't be able to use any app by default. To enable app access for Portal Backend users, it is necessary an specific module "portal_app" that defines the app permissions for this user group.

To create the necessary groups and categories for "portal_app", you can use the following template:

App category inheriting from portal advanced:

.. code-block:: xml

    <record model="ir.module.category" id="category_portal_app">
        <field name="name">Portal app</field>
        <field name="parent_id" ref="portal_backend.category_portal_advanced"/>
    </record>

Group to give access to Portal Backend users to use that app:

.. code-block:: xml

    <record id="group_portal_backend_app" model="res.groups">
        <field name="name">Portal app</field>
        <field name="category_id" ref="category_portal_app"/>
    </record>

You can also create a set of groups that inherit (or not) from each other, but the category always have to be "category_portal_app", because the views are different for each type of user. Here's an example:

.. code-block:: xml

    <record id="group_portal_backend_app_2" model="res.groups">
        <field name="name">Portal app 2</field>
        <field name="category_id" ref="category_portal_app"/>
        <field name="implied_ids" eval="[Command.link(ref('group_portal_backend_app'))]"/>
    </record>


Installation
============

Only install the module.

Configuration
=============

There is nothing to configure.

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

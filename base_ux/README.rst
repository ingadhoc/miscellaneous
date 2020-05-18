.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======
Base UX
=======

Several Improvements:
    * New button to archive/unarchive a mail template in mail template form view.
    * New button to archive/unarchive a company in company form view.
    * New button to add/remove a window action as a contextual action in the windows source model.
    * If a partner is Actived/Archived will be tracked in its message log.
    * When a user marks an activity as done it will be marked done by him instead of mark as done by the activity assigned user
    * Let us to search by exact source the translated terms
    * Be able to use re python library and odoo.tools.html2plaintext()function in server actions, ir.cron, base.automation, etc.
    * New generic wizard that leave us to merge records of any model, By the moment this can be used only via migration script or server action.

    **NOTE:** In order to use it you can go to server actions menu, search by "Merge Records" action and there:

    1. Change the action's model to the model of the records you want to merge.
    2. Add a contextual action in order to see "Merge Records" in the More menu when reviewing list view.
    3. You can also specify the field_list you like in order to pre visualizate the values of the records you want to merge in order to select which will be the final record.

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

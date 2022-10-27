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
    * New button to add/remove a window action as a contextual action in the windows source model.
    * If a partner is Actived/Archived will be tracked in its message log.
    * Be able to use re python library and odoo.tools.html2plaintext()function in server actions, ir.cron, base.automation, etc.
    * Make parent field on res.company invisible as it is useless now
    * Keep the activity's description when changing the activity type, regardless of the activity type's description, and change the activity user only if the activity type has a default user.
    * Make company_registry field on res.company invisible as it is useless now


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

.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=============
POT Generator
=============

Automatic POT (Portable Object Template) file generator for Odoo modules with GitHub API integration.

Features
========

**POT Generation**
  - Generate .pot files using Odoo's native ``trans_export``
  - Direct GitHub API push (no local Git required)
  - Smart content comparison (ignores timestamp changes)

**Integration**
  - Runbot compatible execution
  - Auto-execution on module installation
  - Environment variable configuration

Configuration
=============

Set environment variables for GitHub integration::

    export GITHUB_TOKEN="your_github_token"
    export GITHUB_REPO_OWNER="your_organization"
    export GITHUB_REPO_NAME="your_repository"
    export GITHUB_BRANCH="your_branch"

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

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

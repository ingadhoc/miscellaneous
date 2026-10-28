===============================================
Bank Statement TXT/CSV/XLSX Import Background
===============================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

|badge1| |badge2|

This module extends the **Bank Statement TXT/CSV/XLSX Import** functionality to execute the import process in background jobs, preventing UI blocking during large file imports.

**Table of contents**

.. contents::
   :local:

Overview
========

When importing large bank statement files (TXT/CSV/XLSX), the process can take considerable time and block the user interface. This module integrates the ``account_statement_import_sheet_file`` module with the ``base_bg`` background job system to provide:

* **Asynchronous Import Processing**: Bank statement imports run in background without blocking the UI
* **User Notifications**: Users receive notifications when imports complete with direct links to created statements
* **Better User Experience**: Users can continue working while large imports process in the background
* **Split in Parts**: Large files are split in parts that a worker can finish, each imported by its own job

Features
========

* **Background Processing**: When the ``account_statement_import_sheet_file_bg.rows_per_file_limit`` system parameter holds a number (1000 by default), the import runs in background. Without it, or with a value that is not a number, the import runs right away
* **Split in Parts**: With a sheet mapping, the rows are split in parts of that many rows. Each part keeps the header rows, rows without date are left out, and each part is imported by its own job into a statement named "<name> - Part n/m"
* **Smart Notifications**: Upon completion, users receive notifications with direct links to view the imported bank statements
* **Seamless Integration**: Works transparently with existing sheet file import workflows
* **Error Handling**: When the import of a part fails, the job ends with the error text in its notification
* **Context Preservation**: Original user context and permissions are maintained during background processing

Dependencies
============

This module requires:

* ``base_bg``: Provides the background job processing framework
* ``account_statement_import_sheet_file``: Base functionality for importing bank statements from sheet files
* ``account_statement_import_sheet_file_xlsx``: Reads the parts, which are always written as xlsx

Installation
============

1. Install the required dependencies (``base_bg``, ``account_statement_import_sheet_file`` and ``account_statement_import_sheet_file_xlsx``)
2. Install this module
3. Optionally, change the number of rows per part in the ``account_statement_import_sheet_file_bg.rows_per_file_limit`` system parameter

Usage
=====

The module works transparently with the existing bank statement import process:

1. **Navigate to Bank Statement Import**:

   * Go to *Invoicing > Dashboard* and click on a bank journal
   * Click **Import File** or go directly to *Invoicing > Bank > Bank Statement Import*

2. **Upload Your File**:

   * Select your TXT/CSV/XLSX bank statement file
   * Choose the appropriate statement mapping
   * Click **Import**

3. **Background Processing**:

   * Instead of waiting for the import to complete, you'll receive an immediate notification that the jobs have been queued, one per part
   * You can continue working while the import processes in the background
   * Progress can be monitored in *Settings > Technical > Background Jobs > Jobs*

4. **Completion Notification**:

   * When the import completes successfully, you'll receive a notification with a direct link to view the imported bank statement
   * If the import fails, you'll receive an error notification with details about what went wrong

Example Workflow
================

**Before (Synchronous)**::

   User clicks Import → Wait 5-10 minutes → UI blocked → Import completes

**After (Background)**::

   User clicks Import → Immediate notification "Job queued" → Continue working →
   Receive completion notification with statement link

Background Job Monitoring
=========================

You can monitor import jobs through:

**Settings > Technical > Background Jobs > Jobs**

From here you can:

* **View Job Status**: See if imports are queued, running, completed, or failed
* **Check Progress**: Monitor execution time and completion
* **Retry Failed Jobs**: Manually retry imports that encountered errors
* **View Details**: See complete job information including error messages

Notification System
===================

When a background import completes successfully, users receive an internal message containing:

* **Confirmation**: "The following bank statement has been created"
* **Direct Link**: Clickable link to view the imported statement
* **Statement Name**: Clear identification of the created statement, with " - Part n/m" when the file was split

Error Handling
==============

If an import fails during background processing:

* **User Notification**: The import error is caught and sent to the user as the job result ("Error importing bank statement: ..."), so the job ends as done and is not retried
* **Manual Retry**: Jobs that fail outside the import (for example, the worker is killed) can be retried from the jobs interface

Technical Details
=================

How It Works
------------

1. **Method Override**: The module overrides the ``import_file_button`` method in ``account.statement.import``
2. **Background Enqueueing**: When not already in a background context and the row limit is set, the method is enqueued for background processing. With a sheet mapping, the file is split first and one job is enqueued per part. The file travels to the job as base64 text, in ``wizard_data``, and the job creates a new wizard from it
3. **Context Detection**: Uses ``bg_job`` context flag to prevent infinite recursion
4. **Result Processing**: Extracts statement IDs from the import result and generates user-friendly notifications
5. **URL Generation**: Creates direct links to imported statements for easy access

Code Structure
--------------

.. code-block:: python

    class AccountStatementImport(models.TransientModel):
        _name = "account.statement.import"
        _inherit = ["account.statement.import", "base.bg"]

        def import_file_button(self, wizard_data=None):
            if not self.env.context.get("bg_job") and rows_limit:
                # Split the file and enqueue one job per part
                ...
                self.env[self._name].bg_enqueue("import_file_button", wizard_data=wizard_data)
            else:
                # Recreate the wizard from wizard_data and run the actual import
                result = super(AccountStatementImport, wizard).import_file_button()
                # Return a link to the created statement

Security Considerations
=======================

* **User Context**: Background jobs maintain the original user's security context
* **Permissions**: Import jobs execute with the same permissions as the user who initiated them
* **Data Access**: Users can only access statements they have permission to view
* **Job Visibility**: Users can only see their own background import jobs

Limitations
===========

* **Progress Reporting**: No real-time progress updates during import (inherent limitation of background processing)
* **File Size**: Very large files may still require significant processing time, even in background
* **Context Loss**: Some UI-specific context may not be preserved in background processing

Troubleshooting
===============

Common Issues
-------------

**Import stays in "enqueued" state**

* Check if background job processing is enabled
* Verify cron jobs are running: *Settings > Technical > Automation > Scheduled Actions*
* Check server logs for cron worker errors

**Import fails immediately**

* Verify file format and mapping configuration
* Check user permissions for bank statement creation
* Review error messages in the job details

**Notifications not received**

* Check user notification preferences
* Verify the user has access to the created bank statement
* Check if the import actually completed successfully

**Performance issues**

* Monitor job execution times in the jobs interface
* Consider splitting very large files into smaller chunks
* Check server resources during peak import times

Debug Mode
----------

To debug background imports:

1. Enable developer mode: *Settings > Activate Developer Mode*
2. Check job details: *Settings > Technical > Background Jobs > Jobs*
3. Review server logs for detailed error information
4. Test imports directly before using background processing

Configuration
=============

The module inherits all configuration from its dependencies:

**Statement Sheet Mappings**

Configure file format mappings in *Invoicing > Configuration > Accounting > Statement Sheet Mappings*

**Rows per Part**

The ``account_statement_import_sheet_file_bg.rows_per_file_limit`` system parameter sets the rows of each part (1000 by default). A part of 3000 rows does not finish inside the CPU time a worker is given. Remove the parameter to import right away, without background jobs.

**Background Job Settings**

Background job behavior is controlled by the ``base_bg`` module configuration:

* **Retry Attempts**: Failed jobs are automatically retried (default: 5 times)
* **Processing Frequency**: Jobs are processed every minute by default
* **Timeout Handling**: Long-running jobs are monitored for timeouts

Credits
=======

Authors
-------

* ADHOC SA

Contributors
------------

* ADHOC SA Development Team

Maintainers
-----------

This module is maintained by ADHOC SA.

.. image:: https://www.adhoc.com.ar/logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

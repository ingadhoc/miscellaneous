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
* **Automatic Job Management**: Failed imports are automatically retried with intelligent error handling

Features
========

* **Background Processing**: All bank statement imports from sheet files are automatically processed in background
* **Smart Notifications**: Upon completion, users receive notifications with direct links to view the imported bank statements
* **Seamless Integration**: Works transparently with existing sheet file import workflows
* **Error Handling**: Failed imports are handled gracefully with detailed error reporting
* **Context Preservation**: Original user context and permissions are maintained during background processing

Dependencies
============

This module requires:

* ``base_bg``: Provides the background job processing framework
* ``account_statement_import_sheet_file``: Base functionality for importing bank statements from sheet files

Installation
============

1. Install the required dependencies (``base_bg`` and ``account_statement_import_sheet_file``)
2. Install this module
3. No additional configuration is required

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

   * Instead of waiting for the import to complete, you'll receive an immediate notification that the job has been queued
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
* **Statement Name**: Clear identification of the created statement

Error Handling
==============

If an import fails during background processing:

* **Automatic Retry**: The job will be automatically retried up to the configured limit
* **Error Logging**: Detailed error information is logged for troubleshooting
* **User Notification**: Users are notified of failed imports with error details
* **Manual Retry**: Failed jobs can be manually retried from the jobs interface

Technical Details
=================

How It Works
------------

1. **Method Override**: The module overrides the ``import_file_button`` method in ``account.statement.import``
2. **Background Enqueueing**: When not already in a background context, the method is automatically enqueued for background processing
3. **Context Detection**: Uses ``bg_job`` context flag to prevent infinite recursion
4. **Result Processing**: Extracts statement IDs from the import result and generates user-friendly notifications
5. **URL Generation**: Creates direct links to imported statements for easy access

Code Structure
--------------

.. code-block:: python

    class AccountStatementImport(models.TransientModel):
        _name = "account.statement.import"
        _inherit = ["account.statement.import", "base.bg"]

        def import_file_button(self):
            if not self._context.get("bg_job"):
                # Enqueue for background processing
                return self.bg_enqueue("import_file_button")
            else:
                # Execute the actual import
                result = super().import_file_button()
                # Process result and create notification
                return self._create_completion_notification(result)

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

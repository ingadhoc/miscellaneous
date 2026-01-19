##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging
import uuid

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration script to set batch_key for existing jobs.

    Each existing job will be treated as a single-job batch:
    - batch_key: unique UUID for each job
    """
    cr.execute("""
        SELECT id FROM bg_job
        WHERE batch_key IS NULL
    """)
    job_ids = [row[0] for row in cr.fetchall()]
    updates = [(str(uuid.uuid4()), job_id) for job_id in job_ids]
    cr.executemany(
        """
        UPDATE bg_job
        SET batch_key = %s
        WHERE id = %s
        """,
        updates,
    )

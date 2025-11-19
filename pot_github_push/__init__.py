from . import wizard

import logging
import ast
import os

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Auto-generate POT files on installation

    Environment variables:
        - MODULE_INFO: Dict with tuple key (repo_owner, repo_name) and modules list as value
          {("owner", "repo"): ["module1", "module2"], ...}
        - GITHUB_TOKEN: GitHub token (required)
        - GITHUB_BRANCH: Target branch (required)
    """
    module_info = os.getenv("MODULE_INFO", "{}")
    github_token = os.getenv("GITHUB_TOKEN")
    github_branch = os.getenv("GITHUB_BRANCH")

    if not module_info or module_info == "{}":
        _logger.info("No modules specified for POT generation (MODULE_INFO)")
        return False

    try:
        module_info = ast.literal_eval(module_info)
    except Exception as e:
        _logger.error("Error parsing MODULE_INFO: %s", str(e))
        return False

    env["pot.generator"]._generate_pots(module_info, github_token, github_branch)

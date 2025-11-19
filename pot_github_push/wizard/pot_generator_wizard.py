import base64
import contextlib
import io
import logging

import requests
from odoo import api, models
from odoo.tools.translate import trans_export

_logger = logging.getLogger(__name__)


class PotGenerator(models.AbstractModel):
    _name = "pot.generator"
    _description = "Simple POT Generator"

    @api.model
    def _generate_pots(self, module_info, github_token, github_branch):
        """Generate POT files for specified modules and push to GitHub

        :param module_info: Dict with tuple key (owner, repo) and modules list {("owner", "repo"): ["mod1"]}
        :param github_token: GitHub API token
        :param github_branch: Target branch name
        """
        try:
            for repo_key, module_names in module_info.items():
                # repo_key should be tuple (owner, repo)
                if isinstance(repo_key, tuple):
                    repo_owner, repo_name = repo_key
                else:
                    _logger.error("Invalid repo key type: %s", type(repo_key))
                    continue

                for module_name in module_names:
                    content = self._generate_pot(module_name)
                    if content:
                        self._github_push(module_name, content, repo_owner, repo_name, github_token, github_branch)
            return True

        except Exception as e:
            _logger.exception("POT generation failed: %s", str(e))
            return False

    def _generate_pot(self, module_name):
        """Generate single POT file"""
        try:
            # Get content using Odoo's trans_export
            with contextlib.closing(io.BytesIO()) as buf:
                trans_export(False, [module_name], buf, "po", self.env)
                return buf.getvalue().decode("utf-8")
        except Exception as e:
            _logger.exception("Failed POT generation for %s: %s", module_name, str(e))
            return False

    def _github_push(self, module_name, content, repo_owner, repo_name, github_token, branch):
        """Push POT file to GitHub using API

        :param module_name: Name of the module
        :param content: POT file content
        :param repo_owner: GitHub repository owner
        :param repo_name: GitHub repository name
        :param github_token: GitHub API token
        :param branch: Target branch name
        """
        headers = {}
        try:
            # File path in repository
            file_path = f"{module_name}/i18n/{module_name}.pot"

            # GitHub API headers
            headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github.v3+json"}

            # Get current file SHA (if exists)
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
            params = {"ref": branch}
            response = requests.get(url, headers=headers, params=params, timeout=30)

            sha = None
            if response.status_code == 200:
                file_info = response.json()
                sha = file_info["sha"]

                # Compare content to avoid unnecessary pushes
                existing_content = base64.b64decode(file_info["content"]).decode("utf-8")
                if self._pot_content_equal(existing_content, content):
                    _logger.info("File %s content unchanged (ignoring timestamps), skipping push", file_path)
                    return True

            elif response.status_code == 404:
                _logger.info("File %s does not exist, will create new", file_path)
            else:
                _logger.error("Error getting file info: %s", response.text)
                return False

            content_encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

            # Prepare commit data
            commit_data = {
                "message": f"[I18N] {module_name}: export source terms",
                "content": content_encoded,
                "branch": branch,
            }
            if sha:
                commit_data["sha"] = sha

            # Push to GitHub
            response = requests.put(url, json=commit_data, headers=headers, timeout=30)
            if response.status_code in [200, 201]:
                _logger.info("GitHub push completed for %s", module_name)
                return True
            else:
                _logger.error("GitHub push failed for %s: %s", module_name, response.text)
                return False

        except Exception as e:
            _logger.error("GitHub push failed for %s: %s", module_name, str(e))
            return False
        finally:
            # Clear headers to avoid keeping sensitive token data in memory
            headers.clear()

    def _pot_content_equal(self, content1, content2):
        """Compare POT files ignoring timestamp changes"""

        def normalize_pot_content(content):
            """Remove timestamp lines and normalize content for comparison"""
            lines = content.strip().split("\n")
            normalized_lines = []
            for line in lines:
                # Skip POT-Creation-Date and PO-Revision-Date lines
                if line.startswith('"POT-Creation-Date:') or line.startswith('"PO-Revision-Date:'):
                    continue
                normalized_lines.append(line)
            return "\n".join(normalized_lines)

        normalized1 = normalize_pot_content(content1)
        normalized2 = normalize_pot_content(content2)
        return normalized1 == normalized2

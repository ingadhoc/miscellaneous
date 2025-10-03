from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        user = request.env.user

        session_info = super().session_info()
        if self.env.user.has_group("portal_backend.group_portal_backend"):
            # Add similar session info as internal users get (adapted from native web/models/ir_http.py)
            user_companies = self.env["res.company"].browse(user._get_company_ids()).sudo()
            disallowed_ancestor_companies_sudo = user_companies.parent_ids - user_companies
            all_companies_in_hierarchy_sudo = disallowed_ancestor_companies_sudo + user_companies
            session_info.update(
                {
                    # current_company should be default_company
                    "user_companies": {
                        "current_company": user.company_id.id,
                        "allowed_companies": {
                            comp.id: {
                                "id": comp.id,
                                "name": comp.name,
                                "sequence": comp.sequence,
                                "child_ids": (comp.child_ids & user_companies).ids,
                                "parent_id": comp.parent_id.id,
                                "currency_id": comp.currency_id.id,
                            }
                            for comp in user_companies
                        },
                        "disallowed_ancestor_companies": {
                            comp.id: {
                                "id": comp.id,
                                "name": comp.name,
                                "sequence": comp.sequence,
                                "child_ids": (comp.child_ids & all_companies_in_hierarchy_sudo).ids,
                                "parent_id": comp.parent_id.id,
                            }
                            for comp in disallowed_ancestor_companies_sudo
                        },
                    },
                    "show_effect": True,
                }
            )
        return session_info

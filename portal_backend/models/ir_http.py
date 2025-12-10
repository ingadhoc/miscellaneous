from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        user = request.env.user

        session_info = super().session_info()
        if self.env.user.has_group("portal_backend.group_portal_backend"):
<<<<<<< 48e87b28d371901ad6ea6f896bb13dcc8bb3580d
            # Add similar session info as internal users get (adapted from native web/models/ir_http.py)
            user_companies = self.env["res.company"].browse(user._get_company_ids()).sudo()
            disallowed_ancestor_companies_sudo = user_companies.parent_ids - user_companies
            all_companies_in_hierarchy_sudo = disallowed_ancestor_companies_sudo + user_companies
||||||| 32d3a6492d218095eca4c7bcf23257ed29a2f3bd
            # the following is only useful in the context of a webclient bootstrapping
            # but is still included in some other calls (e.g. '/web/session/authenticate')
            # to avoid access errors and unnecessary information, it is only included for users
            # with access to the backend ('internal'-type users)
            menus = request.env["ir.ui.menu"].load_menus(request.session.debug)
            ordered_menus = {str(k): v for k, v in menus.items()}
            menu_json_utf8 = json.dumps(ordered_menus, default=ustr, sort_keys=True).encode()
            session_info["cache_hashes"].update(
                {
                    "load_menus": hashlib.sha512(menu_json_utf8).hexdigest()[:64],  # sha512/256
                }
            )
=======
            # the following is only useful in the context of a webclient bootstrapping
            # but is still included in some other calls (e.g. '/web/session/authenticate')
            # to avoid access errors and unnecessary information, it is only included for users
            # with access to the backend ('internal'-type users)
            menus = request.env["ir.ui.menu"].load_menus(request.session.debug)
            ordered_menus = {str(k): v for k, v in menus.items()}
            menu_json_utf8 = json.dumps(ordered_menus, default=ustr, sort_keys=True).encode()
            session_info["cache_hashes"].update(
                {
                    "load_menus": hashlib.sha512(menu_json_utf8).hexdigest()[:64],  # sha512/256
                }
            )
            # We need sudo since a user may not have access to ancestor companies
            disallowed_ancestor_companies_sudo = user.company_ids.sudo().parent_ids - user.company_ids
            all_companies_in_hierarchy_sudo = disallowed_ancestor_companies_sudo + user.company_ids
>>>>>>> 15305f046af102d97d6b2f5f553bb93cd75e30a7
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
<<<<<<< 48e87b28d371901ad6ea6f896bb13dcc8bb3580d
                                "child_ids": (comp.child_ids & user_companies).ids,
                                "parent_id": comp.parent_id.id,
                                "currency_id": comp.currency_id.id,
||||||| 32d3a6492d218095eca4c7bcf23257ed29a2f3bd
=======
                                "child_ids": (comp.child_ids & all_companies_in_hierarchy_sudo).ids,
                                "parent_id": comp.parent_id.id,
>>>>>>> 15305f046af102d97d6b2f5f553bb93cd75e30a7
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

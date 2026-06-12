##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import copy

from odoo import Command, api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    access_type = fields.Selection(
        [
            ("internal", "Internal User"),
            ("portal", "Portal"),
            ("portal_backend", "Portal Backend"),
        ],
        compute="_compute_access_type",
        inverse="_inverse_access_type",
        store=True,
        readonly=False,
        help="Single decision point for the user access type. Internal users get backend access "
        "(Role / User or Administrator); Portal and Portal Backend are external users (share=True). "
        "Portal Backend users can additionally be granted Advanced Portal accesses.",
    )
    # Dedicated handle for the Advanced Portal accesses, edited through its own widget; the inverse
    # merges the selection back into group_ids without touching the user-type groups.
    portal_advanced_group_ids = fields.Many2many(
        "res.groups",
        string="Advanced Portal Access",
        compute="_compute_portal_advanced_group_ids",
        inverse="_inverse_portal_advanced_group_ids",
        domain=lambda self: [("privilege_id.category_id", "=", self._portal_advanced_category().id)]
        if self._portal_advanced_category()
        else [("id", "=", False)],
        help="Backend features a Portal Backend user can access (timesheets, holidays, ...). "
        "Provided by the portal_* modules under the Advanced Portal category.",
    )
    # The native groups widget (shown for internal users) lists every category. The Advanced Portal
    # accesses don't belong there (they imply group_portal, incompatible with an internal user), so
    # we drop that category from its hierarchy and expose it separately for our dedicated widget.
    view_group_hierarchy = fields.Json(
        store=False, copy=False, default=lambda self: self._view_group_hierarchy_without_advanced()
    )
    portal_advanced_view_group_hierarchy = fields.Json(
        store=False, copy=False, default=lambda self: self._portal_advanced_view_group_hierarchy()
    )

    def _is_internal(self):
        self.ensure_one()
        if self.sudo().has_group("portal_backend.group_portal_backend") and self.env.context.get("portal_bypass"):
            return True
        return super()._is_internal()

    # -------------------------------------------------------------------------
    # access_type <-> groups
    # -------------------------------------------------------------------------
    @api.depends("group_ids")
    def _compute_access_type(self):
        """Derive the access type from the user groups (source of truth = groups).

        Order matters: an internal user always wins; portal_backend is more specific than
        plain portal (it implies group_portal), so it must be checked first.
        """
        for user in self:
            if user.has_group("base.group_user"):
                user.access_type = "internal"
            elif user.has_group("portal_backend.group_portal_backend"):
                user.access_type = "portal_backend"
            elif user.has_group("base.group_portal"):
                user.access_type = "portal"
            else:
                user.access_type = False

    def _inverse_access_type(self):
        """Translate a manual access_type change into the right groups.

        This is the write/edit path (manual form save). The create path is handled in
        create() so the disjoint constraint never sees two user-type groups together.
        share follows automatically from the groups (it has no inverse of its own).
        """
        for user in self:
            if user.access_type:
                user.group_ids = self._groups_for_access_type(user.group_ids, user.access_type)

    def _view_group_hierarchy_without_advanced(self):
        """Full group hierarchy minus the Advanced Portal category (for the native widget)."""
        hierarchy = copy.deepcopy(self.env["res.groups"]._get_view_group_hierarchy())
        category = self._portal_advanced_category()
        if category:
            hierarchy["categories"] = [c for c in hierarchy["categories"] if c["id"] != category.id]
        return hierarchy

    def _portal_advanced_view_group_hierarchy(self):
        """Only the Advanced Portal category (for the portal_advanced_group_ids widget)."""
        empty = {"groups": {}, "privileges": {}, "categories": []}
        category = self._portal_advanced_category()
        if not category:
            return empty
        full = copy.deepcopy(self.env["res.groups"]._get_view_group_hierarchy())
        categories = [c for c in full["categories"] if c["id"] == category.id]
        if not categories:
            return empty
        privilege_ids = {pid for c in categories for pid in c["privilege_ids"]}
        privileges = {k: v for k, v in full["privileges"].items() if v["id"] in privilege_ids}
        group_ids = {gid for p in privileges.values() for gid in p["group_ids"]}
        groups = {k: v for k, v in full["groups"].items() if v["id"] in group_ids}
        return {"groups": groups, "privileges": privileges, "categories": categories}

    @api.depends("group_ids")
    def _compute_portal_advanced_group_ids(self):
        advanced = self._portal_advanced_groups()
        for user in self:
            user.portal_advanced_group_ids = user.group_ids & advanced

    def _inverse_portal_advanced_group_ids(self):
        advanced = self._portal_advanced_groups()
        for user in self:
            user.group_ids = (user.group_ids - advanced) | user.portal_advanced_group_ids

    @api.model_create_multi
    def create(self, vals_list):
        group_user_id = self.env["ir.model.data"]._xmlid_to_res_id("base.group_user")
        group_portal_id = self.env["ir.model.data"]._xmlid_to_res_id("base.group_portal")
        group_pb_id = self.env["ir.model.data"]._xmlid_to_res_id("portal_backend.group_portal_backend")
        for vals in vals_list:
            access_type = vals.get("access_type")
            # Path B (import via "Groups / Group Name = Role / Portal Backend"): no access_type column,
            # but the backend/portal group arrives through group_ids. Derive the type so the same
            # normalization runs and the stored field/display agree.
            if not access_type and "group_ids" in vals:
                ids = self._resolve_group_ids(vals["group_ids"])
                # Only reclassify when no internal group is imported alongside (group_user wins).
                if group_user_id not in ids and group_pb_id in ids:
                    access_type = vals["access_type"] = "portal_backend"
                elif group_user_id not in ids and group_portal_id in ids:
                    access_type = vals["access_type"] = "portal"
            if access_type in ("portal", "portal_backend"):
                # "Type wins over default": rebuild group_ids without group_user (nor any group that
                # implies it) so the disjoint constraint never trips. We must also inject group_ids
                # when absent, otherwise _default_groups() would add group_user during super().create.
                groups = self.env["res.groups"].browse(self._resolve_group_ids(vals.get("group_ids")))
                target = self._groups_for_access_type(groups, access_type)
                vals["group_ids"] = [Command.set(target.ids)]
                # Reuse an existing contact instead of duplicating it (e.g. importing a portal user
                # whose email already exists as a contact). Without this, _inherits always creates a
                # brand new partner. Mirrors the native "Grant portal access" flow for the import case.
                if not vals.get("partner_id"):
                    partner = self._portal_partner_to_reuse(vals)
                    if partner:
                        vals["partner_id"] = partner.id
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------
    def _groups_for_access_type(self, groups, access_type):
        """Return the target ``res.groups`` recordset for ``access_type``, from ``groups``.

        Strips every group that implies a *different* user type (the disjoint groups
        group_user / group_portal / group_public). This is the key fix: internal application
        groups (e.g. Sales / Purchase added by the *_ux modules) imply group_user, so leaving
        them behind both tripped the disjoint constraint and made the form revert to Internal.
        """
        groups_model = self.env["res.groups"]
        group_user = self.env.ref("base.group_user")
        group_portal = self.env.ref("base.group_portal")
        group_pb = self.env.ref("portal_backend.group_portal_backend")
        user_type_groups = groups_model._get_user_type_groups()
        if access_type == "internal":
            target = group_user
        elif access_type in ("portal", "portal_backend"):
            target = group_portal
        else:
            return groups
        other_types = user_type_groups - target
        # Drop groups implying another user type, plus the user-type groups themselves (re-added below).
        kept = groups.filtered(lambda g: not (g.all_implied_ids & other_types)) - user_type_groups
        if access_type == "internal":
            return kept + group_user
        if access_type == "portal":
            # Plain portal: also drop the backend marker and its Advanced Portal accesses.
            return (kept - group_pb - self._portal_advanced_groups()) + group_portal
        # portal_backend: Advanced Portal accesses (imply group_pb -> group_portal) survive the filter.
        return kept + group_pb

    @api.model
    def _resolve_group_ids(self, group_ids_commands):
        """Resolve a group_ids x2many command list to a concrete set of group ids.

        Tolerant of the forms the web client / importer / ORM may produce:
        ``[(6, 0, [ids])]``, ``[(4, id)]``, ``[(3, id)]``, ``Command.*`` aliases, a bare list of
        ids, or a recordset. For ``create`` there is no pre-existing value, so this is sufficient.
        """
        result = set()
        if not group_ids_commands:
            return result
        if isinstance(group_ids_commands, models.BaseModel):
            return set(group_ids_commands.ids)
        for command in group_ids_commands:
            if isinstance(command, int):
                result.add(command)
            elif isinstance(command, (list, tuple)):
                code = command[0]
                if code in (Command.SET, 6):
                    result = set(command[2])
                elif code in (Command.LINK, 4):
                    result.add(command[1])
                elif code in (Command.UNLINK, Command.DELETE, 3, 2):
                    result.discard(command[1])
                elif code in (Command.CLEAR, 5):
                    result = set()
        return result

    @api.model
    def _portal_partner_to_reuse(self, vals):
        """Existing contact to link instead of creating a new partner, matched by email.

        Only reuses when the match is unambiguous (exactly one contact) and that contact has no
        user yet — the typical "grant portal access to an existing contact" case.
        """
        email = (vals.get("email") or vals.get("login") or "").strip()
        if not email:
            return self.env["res.partner"]
        partners = self.env["res.partner"].search([("email", "=ilike", email), ("user_ids", "=", False)])
        return partners if len(partners) == 1 else self.env["res.partner"]

    @api.model
    def _portal_advanced_category(self):
        return self.env.ref("portal_backend.category_portal_advanced", raise_if_not_found=False)

    def _portal_advanced_groups(self):
        """Groups belonging to the Advanced Portal category (timesheets, holidays, etc.)."""
        category = self._portal_advanced_category()
        if not category:
            return self.env["res.groups"]
        return self.env["res.groups"].sudo().search([("privilege_id.category_id", "=", category.id)])

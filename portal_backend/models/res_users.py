##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api
from odoo.addons.base.models.res_users import Users, name_selection_groups
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from lxml import etree
from lxml.builder import E
import json


def new_check_one_user_type(self):
    """ Monkey patch to bypass this constrain since the portal backend users have portal and portal_backend groups.
        The native method checks if at least there is one user with two user types so it always gonna return False.
        It is necessary to do it as a patch because the constraint is called when a module updates user group.
    """
    return True


Users._check_one_user_type = new_check_one_user_type


class ResUsers(models.Model):

    _inherit = 'res.users'

    @api.model
    def systray_get_activities(self):
        """ We did this to avoid errors when use portal user when the module "Note" is not a depends of this module.
        Only apply this change if the user is portal.
        """
        if self.env.user.has_group('portal_backend.group_portal_backend') and self.env['ir.module.module'].sudo().search(
                [('name', '=', 'note')]).state == 'installed':
            self = self.sudo()
        return super().systray_get_activities()

    def _is_internal(self):
        self.ensure_one()
        if self.has_group('portal_backend.group_portal_backend') and self.env.context.get('portal_bypass'):
            return True
        return super()._is_internal()


class GroupsView(models.Model):
    _inherit = 'res.groups'

    @api.model
    def _update_user_groups_view(self):
        super()._update_user_groups_view()
        if self._context.get('install_filename') or self._context.get(MODULE_UNINSTALL_FLAG):
            return

        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        arch = etree.fromstring(view.arch)

        # Get the user type field name
        category_user_type = self.env.ref('base.module_category_user_type')
        gs = self.get_application_groups([('category_id', '=', category_user_type.id)])
        user_type_field_name = name_selection_groups(gs.ids)

        # Get the portal backend field name
        group_portal_backend = self.env.ref('portal_backend.group_portal_backend')
        category_portal_backend = self.env.ref('portal_backend.category_portal_advanced')

        groups_to_move =[]

        # Remove from internal user view the portal backend groups. There are two cases:
        # Case 1: kind == selection (group string="Advanced portal")
        group = arch.xpath("//group[@string='%s']" % category_portal_backend.name)
        if group:
            group = group[0]
            groups_to_move.append(group)
            group.getparent().remove(group)

        # Case 2: kind == bool (separator string="Child category")
        child_category_names = [category.name for category in category_portal_backend.child_ids]
        for name in child_category_names:
            separator = arch.xpath("//separator[@string='%s']" % name)
            if separator:
                groups_to_move.append(separator[0])
                groups_to_move += self._get_groups_between_separator(separator[0])

        # Create new group for portal backend views
        new_arch_pb_parent_group = E.group(*groups_to_move, invisible=str(user_type_field_name != group_portal_backend.id))

        # Set attributes
        pb_field_attributes = {'readonly': [(user_type_field_name, '!=', group_portal_backend.id)]}
        for field in new_arch_pb_parent_group.iter('field'):
            field.set("invisible", json.dumps(pb_field_attributes))

        # Add the new group to the arch view
        arch.append(new_arch_pb_parent_group)

        # Write the arch on the original view
        xml_content = etree.tostring(arch)
        if xml_content != view.arch:
            new_context = dict(view._context)
            new_context.pop('install_filename', None)
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})

    def _get_groups_between_separator(self, element):
        """ Get all the groups after a determined separator.
        """
        groups = []
        while(True):
            next_element = element.getnext()
            if next_element.tag == "group":
                groups.append(next_element)
                element = next_element
            elif groups:
                for gr in groups:
                    gr.getparent().remove(gr)
                return groups
            else:
                return

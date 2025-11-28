# from odoo import api, models


# class ResPartner(models.Model):
#     _inherit = "res.partner"

#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None, **kwargs):
#         """Use sudo for portal backend users to access partners in message_partner_ids"""
#         if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
#             # When using sudo(), don't pass access_rights_uid as it's not needed
#             return super(ResPartner, self.sudo())._search(domain, offset=offset, limit=limit, order=order, **kwargs)
#         # Only pass access_rights_uid if it was provided
#         if access_rights_uid is not None:
#             return super()._search(
#                 domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid, **kwargs
#             )
#         return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

#     def read(self, fields=None, load="_classic_read"):
#         """Allow portal backend users to read partners"""
#         if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
#             return super(ResPartner, self.sudo()).read(fields=fields, load=load)
#         return super().read(fields=fields, load=load)

#     @api.model
#     def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
#         """Use sudo for portal backend users"""
#         if self.env.user.has_group("portal_timesheet.group_portal_backend_timesheet"):
#             return super(ResPartner, self.sudo()).search_read(
#                 domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs
#             )
#         return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)

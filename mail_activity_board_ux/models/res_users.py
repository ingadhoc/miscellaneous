##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, modules


class ResUsers(models.Model):

    _inherit = 'res.users'

    @api.model
    def activity_user_count(self):
        """ Overwrite in order to separete the crm leads
        """
        res = super(ResUsers, self).activity_user_count()

        # separate the crm.lead leads and opportunities
        for (index, item) in enumerate(res):
            if item.get('model', False) == 'crm.lead':
                res.pop(index)
                self.separete_crm_lead(res)
                break
        return res

    @api.model
    def separete_crm_lead(self, res):
        query = """
            SELECT l.type, count(*), act.res_id, act.res_model as model,
                CASE
                    WHEN %(today)s::date - act.date_deadline::date = 0
                    Then 'today'
                    WHEN %(today)s::date - act.date_deadline::date > 0
                        Then 'overdue'
                    WHEN %(today)s::date - act.date_deadline::date < 0
                    Then 'planned'
                END AS states
            FROM mail_activity AS act
            JOIN ir_model AS m ON act.res_model_id = m.id
            JOIN crm_lead AS l ON act.res_id = l.id
            WHERE act.user_id = %(user_id)s and res_model = 'crm.lead'
            GROUP BY l.type, states, act.res_model, act.res_id;
        """
        self.env.cr.execute(query, {
            'today': fields.Date.context_today(self),
            'user_id': self.env.uid,
        })
        activity_data = self.env.cr.dictfetchall()
        crm_lead_type = dict(
            self.env['crm.lead'].fields_get().get('type').get('selection'))
        user_activities = {}
        for activity in activity_data:
            if not user_activities.get(activity['type']):
                user_activities[activity['type']] = {
                    'name': crm_lead_type[activity['type']],
                    'model': activity['model'],
                    'icon': modules.module.get_module_icon(
                        self.env[activity['model']]._original_module),
                    'total_count': 0,
                    'today_count': 0,
                    'overdue_count': 0,
                    'planned_count': 0,
                    'type': activity['type'],
                }
            user_activities[activity['type']][
                '%s_count' % activity['states']] += activity['count']
            if activity['states'] in ('today','overdue'):
                user_activities[activity['type']][
                    'total_count'] += activity['count']
        res.extend(list(user_activities.values()))
        return res

from odoo.addons.web.controllers.main import ReportController
from odoo.http import route, request


class ReportController(ReportController):

    @route('/report/check_aeroo_pdf/<string:report_name>', type='json',
            auth="user")
    def check_aeroo_pdf(self, report_name):
        report = request.env['ir.actions.report'].sudo()._get_report_from_name(
            report_name)
        return report.out_format.code == 'oo-pdf'

from odoo.tests import TransactionCase


class TestIrActionsServer(TransactionCase):
    def _run_code(self, code):
        partner = self.env["res.partner"].create({"name": "Pedido 123", "comment": "<p>Hola <b>mundo</b></p>"})
        action = self.env["ir.actions.server"].create(
            {
                "name": "Test eval context",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "state": "code",
                "code": code,
            }
        )
        action.with_context(active_model="res.partner", active_id=partner.id).run()
        return partner

    def test_re_functions(self):
        partner = self._run_code(
            "m = re.search(r'Pedido (?P<number>\\d+)', record.name)\n"
            "record.write({'ref': '%s|%s|%s|%s' % (\n"
            "    m.group('number'),\n"
            "    re.sub(r'\\d', 'N', record.name),\n"
            "    ','.join(re.findall(r'^pedido', record.name, re.IGNORECASE)),\n"
            "    bool(re.fullmatch(r'\\w+ \\d+', record.name)),\n"
            ")})"
        )
        self.assertEqual(partner.ref, "123|Pedido NNN|Pedido|True")

    def test_html2plaintext(self):
        partner = self._run_code("record.write({'ref': html2plaintext(record.comment)})")
        self.assertEqual(partner.ref, "Hola *mundo*")

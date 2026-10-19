from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestMaintenanceRating(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.requester = new_test_user(cls.env, login="maintenance_ux_requester", email="requester@example.com")
        cls.technician = new_test_user(
            cls.env, login="maintenance_ux_technician", email="technician@example.com", signature="Tech signature"
        )
        cls.technician_2 = new_test_user(cls.env, login="maintenance_ux_technician_2", email="technician2@example.com")
        cls.template = cls.env.ref("maintenance_ux.mail_template_maintenance_request_rating")

    def _create_request(self, technicians):
        # sudo keeps the requester as create_uid
        request = (
            self.env["maintenance.request"]
            .with_user(self.requester)
            .sudo()
            .create({"name": "Broken screen", "user_ids": [(6, 0, technicians.ids)]})
        )
        return self.env["maintenance.request"].browse(request.id)

    def test_rating_partner_is_request_creator(self):
        request = self._create_request(self.technician)
        self.assertEqual(request._rating_get_partner(), self.requester.partner_id)

    def test_rating_operator_is_the_only_technician(self):
        request = self._create_request(self.technician)
        self.assertEqual(request._rating_get_operator(), self.technician.partner_id)

    def test_rating_operator_empty_without_single_technician(self):
        self.assertFalse(self._create_request(self.env["res.users"])._rating_get_operator())
        self.assertFalse(self._create_request(self.technician | self.technician_2)._rating_get_operator())

    def test_send_rating_creates_pending_rating(self):
        request = self._create_request(self.technician)
        request.action_send_rating()
        rating = request.rating_ids
        self.assertEqual(len(rating), 1)
        self.assertEqual(rating.partner_id, self.requester.partner_id)
        self.assertEqual(rating.rated_partner_id, self.technician.partner_id)
        self.assertFalse(rating.consumed)
        message = request.message_ids.filtered(lambda m: rating.access_token in (m.body or ""))
        self.assertTrue(message, "The rating request with its access token is posted on the request")
        self.assertIn("Tech signature", message.body)

    def test_send_rating_with_several_technicians(self):
        request = self._create_request(self.technician | self.technician_2)
        request.action_send_rating()
        self.assertEqual(len(request.rating_ids), 1)
        self.assertFalse(request.rating_ids.rated_partner_id)

    def test_apply_rating_updates_request_stats(self):
        request = self._create_request(self.technician)
        request.action_send_rating()
        request.rating_apply(5, token=request.rating_ids.access_token, feedback="Good job")
        self.assertTrue(request.rating_ids.consumed)
        self.assertEqual(request.rating_count, 1)
        self.assertEqual(request.rating_last_value, 5)

"""Security checks for user-editable newsletter templates."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from jinja2 import TemplateError

import frappe

from frappe.email.doctype.newsletter.newsletter import Newsletter


class TestNewsletterTemplate(TestCase):
	def test_doc_fields_and_html_still_render(self):
		doc = SimpleNamespace(
			content_type="Rich Text",
			message="<b>{{ doc.subject | upper }}</b>",
			as_dict=lambda: {"subject": "Hello"},
			add_source=lambda html, medium=None: html,
		)
		self.assertEqual(Newsletter.get_message(doc), "<b>HELLO</b>")

	def test_server_apis_cannot_be_called_from_content(self):
		for content_type in ("Rich Text", "HTML"):
			for payload in (
				'{{ frappe.db.set_value("Target DocType", "record", "field", "value") }}',
				'{{ sendmail(recipients="attacker@example.com", subject="test", message="test") }}',
				'{{ frappe.sendmail(recipients="attacker@example.com", subject="test", message="test") }}',
				'{{ doc.callback() }}',
			):
				with self.subTest(content_type=content_type, payload=payload):
					callback = Mock()
					doc = SimpleNamespace(
						content_type=content_type,
						message=payload,
						message_html=payload,
						as_dict=lambda: {"callback": callback},
						add_source=lambda html, medium=None: html,
					)
					with patch.object(frappe.db, "set_value") as write, patch.object(
						frappe, "sendmail"
					) as send:
						with self.assertRaises(TemplateError):
							Newsletter.get_message(doc)
						write.assert_not_called()
						send.assert_not_called()
						callback.assert_not_called()

import unittest
from datetime import datetime

import main


class MainTests(unittest.TestCase):
    def test_parses_day_first_issue_date(self):
        self.assertEqual(
            main.parse_date_from_filename("MyGov 11th August 2026.pdf"),
            datetime(2026, 8, 11),
        )

    def test_parses_month_first_issue_date(self):
        self.assertEqual(
            main.parse_date_from_filename("MyGov August 11, 2026.pdf"),
            datetime(2026, 8, 11),
        )

    def test_repairs_index_php_pdf_path(self):
        url = main.canonical_pdf_url(
            "https://ict.go.ke/index.php/mygov-issues",
            "/index.php/sites/default/files/2026-07/MyGov%207th%20July%202026.pdf",
        )
        self.assertEqual(
            url,
            "https://ict.go.ke/sites/default/files/2026-07/MyGov%207th%20July%202026.pdf",
        )

    def test_rejects_swahili_issue(self):
        self.assertFalse(main.is_english_issue("MyGov Agosti 11, 2026.pdf"))


if __name__ == "__main__":
    unittest.main()

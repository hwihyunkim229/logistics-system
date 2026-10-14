from datetime import datetime, timezone
import unittest

from app.utils.timezone import KST, format_kst, to_kst


class KoreaTimezoneTest(unittest.TestCase):
    def test_naive_database_timestamp_is_already_korea_time(self):
        value = datetime(2026, 10, 14, 9, 30)

        converted = to_kst(value)

        self.assertEqual(converted.replace(tzinfo=None), value)
        self.assertEqual(converted.tzinfo, KST)
        self.assertEqual(format_kst(value), "2026-10-14 09:30:00")

    def test_aware_utc_timestamp_is_converted_to_korea_time(self):
        value = datetime(2026, 10, 14, 0, 30, tzinfo=timezone.utc)

        self.assertEqual(format_kst(value), "2026-10-14 09:30:00")


if __name__ == "__main__":
    unittest.main()

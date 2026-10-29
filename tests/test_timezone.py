from datetime import datetime, timezone
import unittest

from app.utils.timezone import KST, format_kst, kst_to_utc_naive, to_kst


class KoreaTimezoneTest(unittest.TestCase):
    def test_naive_database_timestamp_is_utc_and_converted_to_korea_time(self):
        value = datetime(2026, 10, 14, 0, 30)

        converted = to_kst(value)

        self.assertEqual(converted.replace(tzinfo=None), datetime(2026, 10, 14, 9, 30))
        self.assertEqual(converted.tzinfo, KST)
        self.assertEqual(format_kst(value), "2026-10-14 09:30:00")

    def test_aware_utc_timestamp_is_converted_to_korea_time(self):
        value = datetime(2026, 10, 14, 0, 30, tzinfo=timezone.utc)

        self.assertEqual(format_kst(value), "2026-10-14 09:30:00")

    def test_korea_filter_boundary_is_converted_to_utc_naive(self):
        value = datetime(2026, 10, 14, 0, 0)

        self.assertEqual(kst_to_utc_naive(value), datetime(2026, 10, 13, 15, 0))


if __name__ == "__main__":
    unittest.main()

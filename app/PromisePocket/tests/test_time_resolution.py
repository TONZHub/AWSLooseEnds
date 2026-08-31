from datetime import datetime, timezone
import unittest

from promise_pocket.time_resolution import resolve_due_at


class TimeResolutionTests(unittest.TestCase):
    def test_tomorrow_by_3pm_uses_users_local_date_and_offset(self):
        occurred_at = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)

        resolved = resolve_due_at(
            time_phrase="tomorrow by 3 PM",
            occurred_at=occurred_at,
            timezone_name="America/New_York",
        )

        self.assertEqual("2026-09-01T15:00:00-04:00", resolved.isoformat())

    def test_resolution_respects_dst_change(self):
        occurred_at = datetime(2026, 10, 31, 14, 0, tzinfo=timezone.utc)

        resolved = resolve_due_at(
            time_phrase="tomorrow at 3 PM",
            occurred_at=occurred_at,
            timezone_name="America/New_York",
        )

        self.assertEqual("2026-11-01T15:00:00-05:00", resolved.isoformat())

    def test_utc_timestamp_does_not_shift_tomorrow_to_wrong_local_day(self):
        # 2026-08-31 00:30Z is still the evening of Aug 30 in New York.
        occurred_at = datetime(2026, 8, 31, 0, 30, tzinfo=timezone.utc)

        resolved = resolve_due_at(
            time_phrase="tomorrow by 3 PM",
            occurred_at=occurred_at,
            timezone_name="America/New_York",
        )

        self.assertEqual("2026-08-31T15:00:00-04:00", resolved.isoformat())

    def test_vague_evening_does_not_invent_clock_time(self):
        occurred_at = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)

        resolved = resolve_due_at(
            time_phrase="Tuesday evening",
            occurred_at=occurred_at,
            timezone_name="America/New_York",
        )

        self.assertIsNone(resolved)

    def test_missing_timing_stays_null(self):
        occurred_at = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)

        self.assertIsNone(
            resolve_due_at(
                time_phrase=None,
                occurred_at=occurred_at,
                timezone_name="America/New_York",
            )
        )


if __name__ == "__main__":
    unittest.main()

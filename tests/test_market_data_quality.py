from __future__ import annotations

from datetime import datetime, timezone

from stocks.market_data import _rows_from_dataframe


class FakeDataFrame:
    empty = False

    def __init__(self, rows):
        self.rows = rows

    def reset_index(self):
        return self

    def iterrows(self):
        return iter(enumerate(self.rows))


def test_market_data_rejects_bad_timezone_duplicate_timestamps_and_invalid_prices():
    valid_ts = datetime(2026, 1, 1, 14, 30, tzinfo=timezone.utc)
    later_ts = datetime(2026, 1, 1, 15, 30, tzinfo=timezone.utc)
    rows = [
        {"Datetime": later_ts, "Open": 11, "High": 12, "Low": 10, "Close": 11.5, "Volume": 2000},
        {"Datetime": datetime(2026, 1, 1, 14, 0), "Open": 10, "High": 11, "Low": 9, "Close": 10.5, "Volume": 1000},
        {"Datetime": valid_ts, "Open": 10, "High": 12, "Low": 9, "Close": 11, "Volume": 1000},
        {"Datetime": valid_ts, "Open": 10, "High": 12, "Low": 9, "Close": 11, "Volume": 1000},
        {"Datetime": datetime(2026, 1, 1, 16, 30, tzinfo=timezone.utc), "Open": 0, "High": 12, "Low": 9, "Close": 11, "Volume": 1000},
        {"Datetime": datetime(2026, 1, 1, 17, 30, tzinfo=timezone.utc), "Open": 11, "High": 10, "Low": 9, "Close": 11, "Volume": 1000},
        {"Datetime": datetime(2026, 1, 1, 18, 30, tzinfo=timezone.utc), "Open": 11, "High": 12, "Low": 10, "Close": 11, "Volume": -1},
    ]

    bars = _rows_from_dataframe(FakeDataFrame(rows))

    assert [bar["timestamp"] for bar in bars] == [valid_ts, later_ts]
    assert all(bar["timestamp"].tzinfo is not None for bar in bars)
    assert all(bar["open"] > 0 and bar["close"] > 0 for bar in bars)


def test_market_data_sorts_rows_by_utc_timestamp():
    early = datetime(2026, 1, 1, 14, 30, tzinfo=timezone.utc)
    later = datetime(2026, 1, 1, 15, 30, tzinfo=timezone.utc)
    rows = [
        {"Datetime": later, "Open": 11, "High": 12, "Low": 10, "Close": 11.5, "Volume": 2000},
        {"Datetime": early, "Open": 10, "High": 12, "Low": 9, "Close": 11, "Volume": 1000},
    ]

    bars = _rows_from_dataframe(FakeDataFrame(rows))

    assert [bar["timestamp"] for bar in bars] == [early, later]

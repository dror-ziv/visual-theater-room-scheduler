import logging

import pytest
from datetime import datetime
from schedule_room import _deduce_alternative_time

logger = logging.getLogger()


def test_consecutive_3_hour_window_exists():
    available_windows = [
        datetime(2024, 5, 25, 8, 0),  # 8:00 AM
        datetime(2024, 5, 25, 8, 30),  # 8:30 AM
        datetime(2024, 5, 25, 9, 0),  # 9:00 AM
        datetime(2024, 5, 25, 9, 30),  # 9:30 AM
        datetime(2024, 5, 25, 10, 0),  # 10:00 AM
        datetime(2024, 5, 25, 10, 30),  # 10:30 AM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result == datetime(2024, 5, 25, 8, 0)  # 8:00 AM


def test_no_consecutive_3_hour_window():
    available_windows = [
        datetime(2024, 5, 25, 8, 0),  # 8:00 AM
        datetime(2024, 5, 25, 8, 30),  # 8:30 AM
        datetime(2024, 5, 25, 9, 0),  # 9:00 AM
        datetime(2024, 5, 25, 10, 0),  # 10:00 AM
        datetime(2024, 5, 25, 10, 30),  # 10:30 AM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result is None


def test_empty_list():
    available_windows = []
    result = _deduce_alternative_time(available_windows, logger)
    assert result is None


def test_single_window():
    available_windows = [
        datetime(2024, 5, 25, 8, 0),  # 8:00 AM
        datetime(2024, 5, 25, 8, 30),  # 8:30 AM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result is None


def test_non_consecutive_3_hour_windows():
    available_windows = [
        datetime(2024, 5, 25, 8, 0),  # 8:00 AM
        datetime(2024, 5, 25, 8, 30),  # 8:30 AM
        datetime(2024, 5, 25, 9, 30),  # 9:30 AM
        datetime(2024, 5, 25, 10, 0),  # 10:00 AM
        datetime(2024, 5, 25, 10, 30),  # 10:30 AM
        datetime(2024, 5, 25, 11, 0),  # 11:00 AM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result is None


def test_exactly_3_hour_window():
    available_windows = [
        datetime(2024, 5, 25, 8, 0),  # 8:00 AM
        datetime(2024, 5, 25, 8, 30),  # 8:30 AM
        datetime(2024, 5, 25, 9, 30),  # 9:30 AM
        datetime(2024, 5, 25, 10, 0),  # 10:00 AM
        datetime(2024, 5, 25, 10, 30),  # 10:30 AM
        datetime(2024, 5, 25, 11, 0),  # 11:00 AM
        datetime(2024, 5, 25, 11, 30),  # 11:30 AM
        datetime(2024, 5, 25, 12, 0),  # 12:00 PM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result == datetime(2024, 5, 25, 9, 30)


def test_exactly_3_hour_window_at_end():
    available_windows = [
        datetime(2024, 5, 25, 9, 30),  # 9:30 AM
        datetime(2024, 5, 25, 10, 0),  # 10:00 AM
        datetime(2024, 5, 25, 10, 30),  # 10:30 AM
        datetime(2024, 5, 25, 11, 0),  # 11:00 AM
        datetime(2024, 5, 25, 11, 30),  # 11:30 AM
        datetime(2024, 5, 25, 12, 0),  # 12:00 PM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result == datetime(2024, 5, 25, 9, 30)  # 9:00 AM


def test_3_hour_windows_in_middle_of_list():
    available_windows = [
        datetime(2024, 5, 25, 8, 0),  # 8:00 AM
        datetime(2024, 5, 25, 9, 0),  # 9:00 AM
        datetime(2024, 5, 25, 9, 30),  # 9:30 AM
        datetime(2024, 5, 25, 10, 0),  # 10:00 AM
        datetime(2024, 5, 25, 10, 30),  # 10:30 AM
        datetime(2024, 5, 25, 11, 0),  # 11:00 AM
        datetime(2024, 5, 25, 11, 30),  # 11:30 AM
        datetime(2024, 5, 25, 12, 30),  # 12:30 PM
        datetime(2024, 5, 25, 13, 0),  # 1:00 PM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result == datetime(2024, 5, 25, 9, 0)


def test_3_hour_window_in_end_with_more_than_6_items():
    available_windows = [
        datetime(2024, 5, 25, 8, 0),  # 8:00 AM
        datetime(2024, 5, 25, 8, 30),  # 8:30 AM
        datetime(2024, 5, 25, 9, 0),  # 9:00 AM
        datetime(2024, 5, 25, 10, 0),  # 10:00 AM
        datetime(2024, 5, 25, 10, 30),  # 10:30 AM
        datetime(2024, 5, 25, 11, 0),  # 11:00 AM
        datetime(2024, 5, 25, 11, 30),  # 11:30 AM
        datetime(2024, 5, 25, 12, 0),  # 12:00 PM
        datetime(2024, 5, 25, 12, 30),  # 12:30 PM
        datetime(2024, 5, 25, 13, 0),  # 1:00 PM
        datetime(2024, 5, 25, 13, 30),  # 1:30 PM
        datetime(2024, 5, 25, 14, 0),  # 2:00 PM
        datetime(2024, 5, 25, 14, 30),  # 2:30 PM
    ]
    result = _deduce_alternative_time(available_windows, logger)
    assert result == datetime(2024, 5, 25, 10, 0)

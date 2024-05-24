import logging
import threading
import time
from datetime import datetime, timedelta

from models import ScheduleRoomCommand, SessionCredentials
from visual_theater import query_session_creds, book_room

_STATUS_IDLE = "idle"  # MUST match js code
_STATUS_WAITING_FOR_BOOKING_TO_START = "Waiting for booking to start"
_STATUS_LOGGING_IN = "Logging in"
_STATUS_BOOKING = "Booking"
_STATUS_SUCCESS = "Success"
_STATUS_FAILED = "Failed"
status = _STATUS_IDLE  # this is a global mutable variable that will be used to store the status of the booking process


def _sleep_until(awake_time: datetime):
    now = datetime.now()
    target_time = now.replace(
        hour=awake_time.hour,
        minute=awake_time.minute,
        second=awake_time.second,
        microsecond=0,
    )

    # If the target time is in the past, move it to the next day
    if target_time < now:
        target_time += timedelta(days=1)

    sleep_seconds = (target_time - now).total_seconds()
    time.sleep(sleep_seconds)


_SEND_BOOKING_TIME = datetime(
    year=1, month=1, day=1, hour=8, minute=0, second=0
)  # only time matters

_MAX_RETRIES = 30


def _retry_book_room_until_success(
    creds: SessionCredentials,
    time_: datetime,
    room_id: str,
    max_retries: int,
    logger: logging.Logger,
) -> bool:
    counter = 0
    while not book_room(creds, time_, room_id, logger) and counter < max_retries:
        counter += 1
    # if we succeeded, counter will be less than max_retries
    return counter < max_retries


def schedule_room_thread(meeting: ScheduleRoomCommand, logger: logging.Logger):
    global status
    status = _STATUS_WAITING_FOR_BOOKING_TO_START
    logger.info(f"Waiting for booking to start at {_SEND_BOOKING_TIME}")
    _sleep_until(
        _SEND_BOOKING_TIME - timedelta(seconds=3)
    )  # head start to win the race
    try:
        status = _STATUS_LOGGING_IN
        session_credentials = query_session_creds(meeting.credentials)
        status = _STATUS_BOOKING
        if _retry_book_room_until_success(
            session_credentials, meeting.time, meeting.room, _MAX_RETRIES, logger
        ):
            status = _STATUS_SUCCESS
        else:
            status = _STATUS_FAILED
    except Exception as e:
        print(e)
        status = _STATUS_FAILED


def start_booking_process(meeting: ScheduleRoomCommand, logger: logging.Logger):
    global status
    thread = threading.Thread(target=schedule_room_thread, args=(meeting, logger))
    thread.start()


def real_get_status():
    return status


def set_settings(start_booking_at: datetime, max_retry: int):
    global _SEND_BOOKING_TIME, _MAX_RETRIES
    _SEND_BOOKING_TIME = start_booking_at
    _MAX_RETRIES = max_retry


def get_max_retries():
    return _MAX_RETRIES


def get_send_booking_time():
    return _SEND_BOOKING_TIME

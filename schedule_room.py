import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from models import ScheduleRoomCommand, SessionCredentials
from visual_theater import query_session_creds, book_room, query_rooms

_STATUS_IDLE = "idle"  # MUST match js code
_STATUS_WAITING_FOR_BOOKING_TO_START = "Waiting for booking to start"
_STATUS_LOGGING_IN = "Logging in"
_STATUS_LOGGED_IN = "Logged in"
_STATUS_BOOKING = "Booking"
_STATUS_SUCCESS = "Success"
_STATUS_FAILED = "Failed"
_STATUS_ALTERNATIVE_BOOKING = "Alternative booking"
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
_ALTERNATIVE_BOOKING_ENABLED = True

import platform

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _concurrent_book_room(
    creds: SessionCredentials,
    time_: datetime,
    room_id: str,
    logger: logging.Logger,
) -> bool:
    tasks = []
    duration = 3
    time_between = 0.1
    start_time = datetime.now()
    while datetime.now() - timedelta(seconds=duration) < start_time:
        task = asyncio.create_task(book_room(creds, time_, room_id, logger))
        tasks.append(task)
        await asyncio.sleep(time_between)
    logger.info(f"BookRoomConcurrentTasksStarted: {len(tasks)}")
    results = await asyncio.gather(*tasks)
    return any(results)


def _deduce_alternative_time(
    available_windows: list[datetime], logger: logging.Logger
) -> Optional[datetime]:
    if len(available_windows) < 6:
        return None
    available_windows.sort()

    start_time = available_windows[0]
    current_window = 1
    max_window = 6  # 3 hours represented in half-hour slots

    # Iterate over the available windows
    for i in range(1, len(available_windows)):
        # Check if the current datetime is exactly 30 minutes after the previous one
        if available_windows[i] == start_time + timedelta(minutes=30 * current_window):
            current_window += 1
        else:
            start_time = available_windows[i]
            current_window = 1

        # Check if we found a 3-hour consecutive window
        if current_window == max_window:
            logger.info(f"AlternativeTimeDeduced: {start_time}")
            return start_time

    # If no 3-hour window was found, return None
    return None


def _query_room_available_slots(
    creds: SessionCredentials,
    time_: datetime,
    room_id: str,
    logger: logging.Logger,
) -> list[datetime]:
    for room in query_rooms(creds.cookie, time_, logger):
        if room.id == room_id:
            return room.available_slots
    logger.error(f"RoomNotFoundError: {room_id}")
    return []


_MAX_ALTERNATIVE_RETRIES = 5


def _best_effort_alternative_booking(
    creds: SessionCredentials,
    time_: datetime,
    room_id: str,
    logger: logging.Logger,
) -> bool:
    for counter in range(_MAX_ALTERNATIVE_RETRIES):
        new_time = _deduce_alternative_time(
            _query_room_available_slots(creds, time_, room_id, logger), logger
        )
        if new_time is None:
            return False
        if asyncio.run(book_room(creds, new_time, room_id, logger)):
            return True
    logger.info("AlternativeBookingExceededMaxRetries")
    return False


def schedule_room_thread(meeting: ScheduleRoomCommand, logger: logging.Logger):
    global status
    status = _STATUS_WAITING_FOR_BOOKING_TO_START
    logger.info(f"Waiting for booking to start at {_SEND_BOOKING_TIME}")
    _sleep_until(
        _SEND_BOOKING_TIME - timedelta(seconds=10)
    )  # head start to win the race
    try:
        status = _STATUS_LOGGING_IN
        session_credentials = query_session_creds(meeting.credentials)
        status = _STATUS_LOGGED_IN
        _sleep_until(_SEND_BOOKING_TIME - timedelta(seconds=1))
        status = _STATUS_BOOKING
        if asyncio.run(
            _concurrent_book_room(
                session_credentials, meeting.time, meeting.room, logger
            )
        ):
            status = _STATUS_SUCCESS
            return
        if _ALTERNATIVE_BOOKING_ENABLED:
            status = _STATUS_ALTERNATIVE_BOOKING
            if _best_effort_alternative_booking(
                session_credentials, meeting.time, meeting.room, logger
            ):
                status = _STATUS_SUCCESS
                return
        status = _STATUS_FAILED
    except Exception as e:
        logger.error(f"ScheduleRoomTaskFailed: {e}")
        status = _STATUS_FAILED


def start_booking_process(meeting: ScheduleRoomCommand, logger: logging.Logger):
    thread = threading.Thread(target=schedule_room_thread, args=(meeting, logger))
    thread.start()


def real_get_status():
    return status


def set_settings(start_booking_at: datetime, alternative_booking: bool):
    global _SEND_BOOKING_TIME, _ALTERNATIVE_BOOKING_ENABLED
    _SEND_BOOKING_TIME = start_booking_at
    _ALTERNATIVE_BOOKING_ENABLED = alternative_booking


def get_send_booking_time():
    return _SEND_BOOKING_TIME

def get_alternative_bookings():
    return _ALTERNATIVE_BOOKING_ENABLED
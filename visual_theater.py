import logging

from datetime import datetime
from typing import Optional

import aiohttp

from models import Credentials, SessionCookie, Room, FormToken, SessionCredentials

import requests
from bs4 import BeautifulSoup, Tag


def log_in(creds: Credentials) -> SessionCookie:
    session = requests.Session()
    url = "https://students.visualtheatre.co.il/he"
    headers = {
        "user-agent": "",  # must be included but can be empty
    }
    data = {
        "name": creds.username,
        "pass": creds.password,
        "form_id": "user_login",
        "op": "%D7%9B%D7%A0%D7%99%D7%A1%D7%94",  # "כניסה" in hebrew
    }

    response = session.post(url, headers=headers, data=data)
    return SessionCookie(session.cookies.get_dict())


def _is_available_slot(li: Tag, logger: logging.Logger) -> bool:
    if "room-info" in li.get("class", []) or "timeslot" in li.get(
        "class", []
    ):  # metadata, not a time slot
        return False
    elif "closed" in li.get("class", []) or "booked" in li.get("class", []):
        return False
    elif "reservable" in li.get("class", []):
        return True
    else:
        logger.error(f"Unknown slot status: {li}")
        return False


def _parse_available_slots(
    room: BeautifulSoup, logger: logging.Logger
) -> list[datetime]:
    """
    we do not get the time of unavailable slots, so we only parse the available ones
    """
    for li in room.select("li"):
        if _is_available_slot(li, logger):
            # slot link is "/he/node/add/room-reservations-reservation/{month}/{day}/{hourminute}/{room_id}"
            slot_link = li.select_one(".booking-span a")["href"]
            time = slot_link.split("/")[-2]
            hour = time[:2]
            minute = time[2:]
            day = slot_link.split("/")[-3]
            month = slot_link.split("/")[-4]
            yield datetime(
                year=1,  # year is not provided
                month=int(month),
                day=int(day),
                hour=int(hour),
                minute=int(minute),
            )


def _room_id(metadata: Tag) -> str:
    """
    url of room metadata is "/he/node/{room_id}"
    """
    return metadata.select_one("a")["href"].split("/")[-1]


def _parse_room(room: BeautifulSoup, logger: logging.Logger) -> Optional[Room]:
    """
    room metadata is a li with class "room-info"
    room slots are lis nested in the room div
    metadata text value is the room name
    """
    metadata = room.find("li", class_="room-info")
    if metadata is None:
        logger.error(f"Room metadata not found in {room}")
        return None

    return Room(
        name=metadata.text.strip(),
        id=_room_id(metadata),
        available_slots=list(_parse_available_slots(room, logger)),
    )


def _rooms(response: BeautifulSoup) -> list[BeautifulSoup]:
    """
    rooms are divs with class "grid-column hours-column" nested in div with id "halls"
    excluding rooms without a link to their metadata
    """
    rooms = response.find("div", id="halls").find_all(
        "div", class_="grid-column hours-column"
    )
    result = []
    for room in rooms:
        if (
            room.find("li", class_="room-info").select_one("a") is None
        ):  # not an actual room
            continue
        result.append(room)
    return result


def _parse_rooms(html: str, logger: logging.Logger) -> list[Room]:
    soup = BeautifulSoup(html, "html.parser")
    for room in _rooms(soup):
        if parsed_room := _parse_room(room, logger):
            yield parsed_room


def _query_rooms(cookie: SessionCookie, date: datetime) -> str:
    # url date and month must be two-digit numbers (e.g. 01 not 1)
    url = f"https://students.visualtheatre.co.il/he/room_reservations/{date.strftime('%m')}/{date.strftime('%d')}"
    headers = {
        "user-agent": "",  # must be included but can be empty
    }
    response = requests.get(url, headers=headers, cookies=cookie)
    return response.text


def _query_form_token(cookie: SessionCookie) -> str:
    """
    we must query a room reservations page to get the form token
    it does not have to be a valid page because we only need the token
    https://students.visualtheatre.co.il/he/node/add/room-reservations-reservation/{month}/{day}/{hourminute}/{room_id}
    """
    time_right_now = datetime.now()
    room_number = 14343  # arbitrary existing room number
    url = f"https://students.visualtheatre.co.il/he/node/add/room-reservations-reservation/{time_right_now.month}/{time_right_now.day}/{time_right_now.strftime('%H%M')}/{room_number}"
    headers = {
        "user-agent": "",  # must be included but can be empty
    }
    response = requests.get(url, headers=headers, cookies=cookie)
    return response.text


def _parse_page_date(html: str) -> datetime:
    soup = BeautifulSoup(html, "html.parser")
    date = soup.find("div", class_="hours")
    return datetime.strptime(date, "%Y-%m-%d")


def _is_valid_data(rooms: list[Room], queried_date: datetime) -> bool:
    """
    when something goes wrong, response defaults to returning the rooms of today.
    if queries date does not match the response date, the data is invalid
    we only check with one of the rooms and assume all rooms have the same date
    we only check month and dat because year is not provided
    """
    if not rooms:
        return False
    slot_to_compare = None
    for room in rooms:
        if slots := room.available_slots:
            slot_to_compare = slots[0]
            break

    if slot_to_compare is None:
        return False
    return (
        slot_to_compare.month == queried_date.month
        and slot_to_compare.day == queried_date.day
    )


def _parse_form_token(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    token = soup.find("input", {"name": "form_token"})
    return token["value"]


def query_rooms(
    cookie: SessionCookie, date: datetime, logger: logging.Logger
) -> list[Room]:
    response = _query_rooms(cookie, date)
    result = list(_parse_rooms(response, logger))
    if not _is_valid_data(result, date):
        raise ValueError(f"Invalid data for date {date}")
    return result


def query_form_token(cookie: SessionCookie) -> FormToken:
    return FormToken(_parse_form_token(_query_form_token(cookie)))


async def _request_book_meeting(
    creds: SessionCredentials, time: datetime, room_id: str
) -> str:
    """
    url is "/he/node/add/room-reservations-reservation/{month}/{day}/{hourminute}/{room_id}"

    """
    url = f"https://students.visualtheatre.co.il/he/node/add/room-reservations-reservation/{time.month}/{time.day}/{time.strftime('%H%M')}/{room_id}"
    headers = {
        "user-agent": "",  # must be included but can be empty
    }
    date_right_now = datetime.now()
    payload = {
        "form_token": creds.form_token,
        "form_id": "room_reservations_reservation_node_form",
        "reservation_length[und]": "180",  # 3 hours
        "reservation_repeat_until[und][0][value][year]": date_right_now.year,
        "reservation_repeat_until[und][0][value][month]": date_right_now.month,
        "reservation_repeat_until[und][0][value][day]": date_right_now.day,
        "op": "שמירה",  # "save" in hebrew
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, headers=headers, cookies=creds.cookie, data=payload
        ) as response:
            return await response.text()


def _parse_booking_confirmation_message(html: str, logger: logging.Logger) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if response_message := soup.find(
        "div",
        class_="alert-dismissible",
    ):
        return response_message.text
    elif response_message := soup.find(
        "div",
        class_="messages error",
    ):
        return response_message.text
    else:
        logger.error(f"Booking response message not found in {soup}")
        return ""


def _is_booking_successful(message: str) -> bool:
    """
    this is a successful message:
    '\n×\nהודעת סטטוס\nהזמנות חדרים - הזמנה שםפרטי שםמשפחה נוצר.'
    """
    if "נוצר" in message:
        return True
    return False


async def book_room(
    creds: SessionCredentials, time: datetime, room_id: str, logger: logging.Logger
) -> bool:
    logger.info(f"RoomBookingAttempted")
    response = await _request_book_meeting(creds, time, room_id)
    message = _parse_booking_confirmation_message(response, logger)
    logger.info(f"RoomBookingResponseMessage: {message}")
    return _is_booking_successful(message)


def query_session_creds(creds: Credentials) -> SessionCredentials:
    cookie = log_in(creds)
    form_token = query_form_token(cookie)
    return SessionCredentials(cookie=cookie, form_token=form_token)

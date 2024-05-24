import json
import logging
import sys
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter(
    "%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s"
)
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

logger.info("API is starting up")


from datetime import datetime, timedelta


from schedule_room import (
    start_booking_process,
    real_get_status,
    set_settings,
    get_max_retries,
    get_send_booking_time,
)
from models import ScheduleRoomCommand, Credentials


templates = Jinja2Templates(directory="templates")

_INDEX_FILE_PATH = "index.html"


def _time_slots() -> list[str]:
    time_slots = []
    for hour in range(8, 22):
        for minute in range(0, 60, 30):
            time_slots.append(f"{hour:02d}:{minute:02d}")
    return time_slots


def _date_slots() -> list[str]:
    date_slots = []
    for i in range(0, 18):
        date_slots.append((datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d"))
    # from latest to oldest
    date_slots.sort(reverse=True)
    return date_slots


_ROOMS_TO_IDS = {
    "חדר תפירה- סטודיו נקי": "14349",
    "ביהס למוזיקה מן המזרח": "123666",
    "תיאטרון סופר מריו": "14348",
    "האולם הלבן": "14343",
    "כיתה 2": "14351",
    "יד חרוצים": "14347",
    "אולפן": "14350",
}


def _landing_page(request: Request):
    return templates.TemplateResponse(
        request,
        _INDEX_FILE_PATH,
        context={
            "time_slots": _time_slots(),
            "date_slots": _date_slots(),
            "rooms": _ROOMS_TO_IDS,
            "max_retry": get_max_retries(),
            "start_at": get_send_booking_time().strftime("%H:%M"),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return _landing_page(request)


@app.post("/book_meeting", response_class=HTMLResponse)
async def schedule_room(
    request: Request,
    meeting_time: str = Form(...),
    meeting_date: str = Form(...),
    room: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    time = datetime.strptime(f"{meeting_date} {meeting_time}", "%Y-%m-%d %H:%M")
    assert time.minute in [0, 30]  # only on the hour or half hour
    meeting = ScheduleRoomCommand(
        time=time,
        room=room,
        credentials=Credentials(username=username, password=password),
    )
    start_booking_process(meeting, logger)
    return RedirectResponse(url="/", status_code=303)


@app.get("/get_status", response_class=HTMLResponse)
async def get_status(request: Request):
    status = real_get_status()
    return json.dumps({"status": status})


@app.post("/settings", response_class=HTMLResponse)
async def settings_landing(
    request: Request,
    start_booking_at: str = Form(...),
    max_retry: str = Form(...),
):
    set_settings(
        start_booking_at=datetime.strptime(start_booking_at, "%H:%M"),
        max_retry=int(max_retry),
    )
    return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

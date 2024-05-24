# Visual Arts Room Scheduler
Tired of waking up early and still losing the race to book a room?\
This project ensures you'll never miss out on securing a spot, no matter how competitive it gets.\
Works for [Visual Theatre](https://students.visualtheatre.co.il/) only.

<img width="300" alt="image" src="https://github.com/dror-ziv/visual-theater-room-scheduler/assets/84446205/ec834cdf-e882-4503-b497-b0f4066591a5">

# Overview

This project allows you to preconfigure your room booking specifications, handling everything automatically to ensure you're first in line when the booking window opens.\
It also includes a retrying mechanism to maximize your chances of securing a spot, even if the first attempt fails.

It is basically a simple FastApi front that interact with the backend schedule a task of booking a room at a specific time.\
The backend is a python script that uses threading to handle the time-sensitive booking operations, including authentication and form token handling.\
Most of the complexity writing this was API research.


## Features
* Preconfiguration of Booking Details
* Automated Booking System
* Retry Logic
* Real-time Status Updates

## Tech Stack
* Frontend: FastAPI for the web framework, JavaScript for client-side logic, HTML for presentation.
* Backend: Python, with threading, handling booking operations, including authentication and form token handling.


## Getting Started

* Clone this repository.
```bash
pip intall -r requirements.txt
python main.py
```
* Go to `http://127.0.0.1:8000`

# Future Enhancements
* Improved Failure Handling: If your initial booking attempt fails, the system will soon be able to find the next best slot and book it before anyone else even has a chance!
## Why This Project?
I Wrote this project to help a friend who was tired of waking up early and still losing the race.
Now he can sleep in.

Feel free to contribute to the project or fork it to adapt to other booking needs. Never lose the race again!


import os
import json
import random
from dotenv import load_dotenv
import gradio as gr
from openai import OpenAI

import base64
from io import BytesIO
from PIL import Image
from pydub import AudioSegment
import subprocess
import tempfile
import time

########################################
# 1) Environment & Model Setup
########################################
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
else:
    print("OpenAI API Key not set")

MODEL = "gpt-4o-mini"
openai = OpenAI()

########################################
# 2) System Prompt
########################################
system_message = (
    "You are a helpful assistant for an Airline called FlightAI.\n\n"
    "When the user wants to book a flight, follow these steps:\n"
    "1. Ask for the source city.\n"
    "2. Ask for the destination city (must be different from source).\n"
    "3. Call the function 'check_flight_availability' with the user's destination.\n"
    "   - If it returns an empty list, say: 'No flights to that city'.\n"
    "   - If it returns flights, list them EXACTLY, in a numbered list, showing airline, time, price, and duration.\n"
    "4. Wait for the user to pick one flight option by number.\n"
    "5. Then ask for passenger first name, last name, and age.\n"
    "6. Finally call 'book_flight' to confirm and show the user the real seat number and booking details.\n\n"
    "You also have a tool 'generate_report' which summarizes ALL booked tickets in a single file.\n\n"
    "IMPORTANT:\n"
    "- Always call 'check_flight_availability' if user mentions a new destination.\n"
    "- Do not invent flights or seat numbers. Use what the function calls return.\n"
    "- Source and destination cannot be the same.\n"
    "- Every time a flight is booked, produce a new ticket file named firstName_lastName_bookingNumber.txt.\n"
    "- If a city is not in flight_availability, say 'No flights found for that city'.\n"
    "If the user wants all tickets summarized, call 'generate_report' with no arguments (the function has none).\n"
    "If you don't know something, say so.\n"
    "Keep answers short and courteous.\n"
)

########################################
# 3) Flight Data & Bookings
########################################
flight_availability = {
    "london": [
        {"airline": "AirlinesAI", "time": "10:00 AM", "price": "$799",  "duration": "8 hours"},
        {"airline": "IndianAirlinesAI", "time": "3:00 PM", "price": "$899",  "duration": "8 hours"},
        {"airline": "AmericanAirlinesAI","time": "8:00 PM", "price": "$999",  "duration": "8 hours"},
    ],
    "paris": [
        {"airline": "EuropeanAirlinesAI","time": "11:00 AM","price": "$399",  "duration": "7 hours"},
        {"airline": "BudgetAirlines",    "time": "6:00 PM", "price": "$2399", "duration": "7 hours"},
    ],
    "tokyo": [
        {"airline": "TokyoAirlinesAI",   "time": "12:00 PM","price": "$4000", "duration": "5 hours"},
        {"airline": "FastFly",           "time": "7:00 PM", "price": "$1400", "duration": "5 hours"},
    ],
    "berlin": [
        {"airline": "BerlinAirlinesAI",  "time": "9:00 AM", "price": "$499",  "duration": "6 hours"},
        {"airline": "AmericanAirlinesAI","time": "4:00 PM", "price": "$899",  "duration": "6 hours"},
    ],
    "nagpur": [
        {"airline": "IndianAirlinesAI",  "time": "8:00 AM", "price": "$1000", "duration": "10 hours"},
        {"airline": "JetAirlines",       "time": "2:00 PM", "price": "$1500", "duration": "10 hours"},
        {"airline": "AirlinesAI",        "time": "10:00 PM","price": "$800",  "duration": "10 hours"},
    ],
}
flight_bookings = []

########################################
# 4) Helper Functions
########################################
def generate_seat_numbers(seed_value):
    random.seed(seed_value)
    return [
        f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1, 99):02}"
        for _ in range(5)
    ]

def check_flight_availability(destination_city: str):
    print(f"[TOOL] check_flight_availability({destination_city})")
    city = destination_city.lower()
    return flight_availability.get(city, [])

def generate_ticket_file(booking_dict, booking_number):
    fname = booking_dict["first_name"].replace(" ", "_")
    lname = booking_dict["last_name"].replace(" ", "_")
    filename = f"{fname}_{lname}_{booking_number}.txt"

    content = (
        "Flight Ticket\n"
        "=============\n"
        f"Booking #   : {booking_number}\n"
        f"Passenger   : {booking_dict['first_name']} {booking_dict['last_name']}, Age {booking_dict['age']}\n"
        f"Source      : {booking_dict['source']}\n"
        f"Destination : {booking_dict['destination']}\n"
        f"Airline     : {booking_dict['airline']}\n"
        f"Departure   : {booking_dict['time']}\n"
        f"Price       : {booking_dict['price']}\n"
        f"Duration    : {booking_dict['duration']}\n"
        f"Seat Number : {booking_dict['seat']}\n"
    )
    with open(filename, "w") as f:
        f.write(content)

    print(f"[TOOL] Ticket file generated => {filename}")
    return filename

def book_flight(source, destination, option_index, first_name, last_name, age):
    print(f"[TOOL] book_flight({source=}, {destination=}, {option_index=})")

    if source.lower() == destination.lower():
        return "Error: source and destination must not be the same."

    try:
        idx = int(option_index)
    except ValueError:
        return "Error: flight option number is not a valid integer."

    flights = check_flight_availability(destination)
    if not flights:
        return f"Error: No flights found for {destination.title()}."

    pick = idx - 1
    if pick < 0 or pick >= len(flights):
        return f"Error: Invalid flight option #{idx} for {destination.title()}."

    chosen_flight = flights[pick]
    airline   = chosen_flight["airline"]
    dep_time  = chosen_flight["time"]
    price     = chosen_flight["price"]
    duration  = chosen_flight["duration"]

    seat_list = generate_seat_numbers(hash(destination + airline + str(len(flight_bookings))))
    chosen_seat = seat_list[0]

    new_booking = {
        "source":      source.title(),
        "destination": destination.title(),
        "airline":     airline,
        "time":        dep_time,
        "price":       price,
        "duration":    duration,
        "seat":        chosen_seat,
        "first_name":  first_name.title(),
        "last_name":   last_name.title(),
        "age":         age,
    }
    flight_bookings.append(new_booking)

    booking_number  = len(flight_bookings)
    ticket_filename = generate_ticket_file(new_booking, booking_number)

    confirmation = (
        f"Booking #{booking_number} confirmed for {first_name.title()} {last_name.title()}. "
        f"Flight from {source.title()} to {destination.title()} on {airline} at {dep_time}. "
        f"Ticket saved to {ticket_filename}."
    )
    print(f"[TOOL] {confirmation}")
    return confirmation

def generate_report():
    print(f"[TOOL] generate_report called.")
    report_content = "Flight Booking Summary Report\n"
    report_content += "=============================\n"

    if not flight_bookings:
        report_content += "No bookings found.\n"
    else:
        for i, booking in enumerate(flight_bookings, start=1):
            report_content += (
                f"Booking #   : {i}\n"
                f"Passenger   : {booking['first_name']} {booking['last_name']}, Age {booking['age']}\n"
                f"Source      : {booking['source']}\n"
                f"Destination : {booking['destination']}\n"
                f"Airline     : {booking['airline']}\n"
                f"Departure   : {booking['time']}\n"
                f"Price       : {booking['price']}\n"
                f"Duration    : {booking['duration']}\n"
                f"Seat Number : {booking['seat']}\n"
                "-------------------------\n"
            )

    filename = "summary_report.txt"
    with open(filename, "w") as f:
        f.write(report_content)

    msg = f"Summary report generated => {filename}"
    print(f"[TOOL] {msg}")
    return msg

########################################
# Image & Audio
########################################
def artist(city):
    print(f"[artist] Generating an image for {city}")
    image_response = openai.images.generate(
        model="dall-e-3",
        prompt=f"An image representing a vacation in {city}, showing tourist spots in a vibrant pop-art style",
        size="1024x1024",
        n=1,
        response_format="b64_json",
    )
    image_base64 = image_response.data[0].b64_json
    image_data = base64.b64decode(image_base64)
    return Image.open(BytesIO(image_data))

def play_audio(audio_segment):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "temp_audio.wav")
    try:
        audio_segment.export(temp_path, format="wav")
        time.sleep(1)
        subprocess.call(
            ["ffplay", "-nodisp", "-autoexit", "-hide_banner", temp_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    finally:
        try:
            os.remove(temp_path)
        except:
            pass

def talker(message):
    print("[talker] Generating TTS for final reply...")
    response = openai.audio.speech.create(
        model="tts-1",
        voice="onyx",  # or "alloy"
        input=message
    )
    audio_stream = BytesIO(response.content)
    audio = AudioSegment.from_file(audio_stream, format="mp3")
    play_audio(audio)

########################################
# 5) Tools JSON Schemas
########################################
price_function = {
    "name": "get_ticket_price",
    "description": "Get the price of a return ticket for the city from flight list data.",
    "parameters": {
        "type": "object",
        "properties": {
            "destination_city": {
                "type": "string",
                "description": "City name.",
            },
        },
        "required": ["destination_city"],
    },
}

availability_function = {
    "name": "check_flight_availability",
    "description": (
        "Check flight availability for the specified city. "
        "Returns a list of {airline, time, price, duration}."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "destination_city": {
                "type": "string",
                "description": "City name to check in flight_availability dict.",
            },
        },
        "required": ["destination_city"],
    },
}

book_function = {
    "name": "book_flight",
    "description": (
        "Book a flight using an option index for the chosen city. "
        "Generates a unique ticket file firstName_lastName_{bookingNumber}.txt each time."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "User's source city (must differ from destination).",
            },
            "destination": {
                "type": "string",
                "description": "User's destination city.",
            },
            "option_index": {
                "type": "string",
                "description": "1-based flight option number the user selected from check_flight_availability.",
            },
            "first_name": {
                "type": "string",
                "description": "Passenger's first name.",
            },
            "last_name": {
                "type": "string",
                "description": "Passenger's last name.",
            },
            "age": {
                "type": "string",
                "description": "Passenger's age.",
            },
        },
        "required": ["source", "destination", "option_index", "first_name", "last_name", "age"],
    },
}

report_function = {
    "name": "generate_report",
    "description": (
        "Generates a summary report of ALL tickets in summary_report.txt."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

tools = [
    {"type": "function", "function": price_function},
    {"type": "function", "function": availability_function},
    {"type": "function", "function": book_function},
    {"type": "function", "function": report_function},
]

########################################
# 6) Handling the Tool Calls
########################################
def handle_tool_call(message):
    """
    Called if LLM tries to call one of the 4 tools.
    If the tool is 'book_flight', we also capture the 'destination' so we can
    possibly generate an image for it if the user wants that.
    """
    tool_call = message.tool_calls[0]
    fn_name   = tool_call.function.name
    args      = json.loads(tool_call.function.arguments)

    # We'll keep track of the 'dest_city' if the function is 'book_flight'
    # so we can generate an image for that city if the user wants to.
    dest_city = None

    if fn_name == "get_ticket_price":
        city = args.get("destination_city")
        flights = check_flight_availability(city)
        if not flights:
            response_content = {"destination_city": city, "price": "No flights found."}
        else:
            response_content = {
                "destination_city": city,
                "price": flights[0]["price"]
            }

    elif fn_name == "check_flight_availability":
        city = args.get("destination_city")
        flights = check_flight_availability(city)
        response_content = {"destination_city": city, "availability": flights}

    elif fn_name == "book_flight":
        src  = args.get("source")
        dest = args.get("destination")
        idx  = args.get("option_index")
        fnam = args.get("first_name")
        lnam = args.get("last_name")
        age  = args.get("age")

        confirmation = book_flight(src, dest, idx, fnam, lnam, age)
        response_content = {
            "source": src,
            "destination": dest,
            "option_index": idx,
            "first_name": fnam,
            "last_name":  lnam,
            "age":        age,
            "confirmation": confirmation
        }
        dest_city = dest  # track for potential image generation

    elif fn_name == "generate_report":
        msg = generate_report()
        response_content = {"report": msg}

    else:
        response_content = {"error": f"Unknown tool: {fn_name}"}

    return {
        "role": "tool",
        "content": json.dumps(response_content),
        "tool_call_id": tool_call.id,
    }, dest_city


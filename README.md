# **Important Features of Airline AI Assistant**

### ✈️ **Flight Availability**
- Check available flights to a destination with:
  - Airline name, departure time, price, and duration.
- Alerts user if no flights are found.

### 🛫 **Step-by-step Flight Booking**
- Guides users through:
  1. Selecting source and destination cities.
  2. Choosing a flight option.
  3. Providing passenger details (name, age).
- Ensures source and destination are not the same.

### 🌛 **Ticket Generation**
- Creates a unique ticket file: `firstName_lastName_bookingNumber.txt`.
- Ticket includes:
  - Passenger details
  - Flight details (airline, time, price, seat number)

### 📊 **Generate Summary Report**
- Summarizes all bookings into a single file: `summary_report.txt`.
- Includes all flight and passenger details for review or administration.

### 🪑 **Automated Seat Assignment**
- Assigns a random but consistent seat number for each booking.
- Ensures unique seats for each flight.

### 💬 **Interactive Chat Interface**
- Real-time conversation via Gradio.
- Provides clear, polite responses based on user input.

### 🛠️ **Modular Tool Support**
- Integrated tools for:
  - Checking flight availability
  - Booking flights
  - Generating reports
- Easily extensible for future features.

### 🛡️ **Error Handling**
- Validates user inputs and prevents invalid bookings.
- Graceful error messages for smooth user experience.

---

These features ensure a seamless, user-friendly experience while booking flights or managing ticket details!

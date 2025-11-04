from flask import Flask, render_template_string
import pdfplumber
import requests
from bs4 import BeautifulSoup
import datetime

app = Flask(__name__)

def get_pdf_url():
    # Get the webpage content
    url = 'https://quwwatulislam.org/prayertimes/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the PDF link using the selector
    pdf_url = soup.select_one('.post-content a').get('href')
    return pdf_url

def get_prayer_times():
    import io
    import re

    pdf_url = get_pdf_url()
    response = requests.get(pdf_url)
    pdf_file = io.BytesIO(response.content)

    today = datetime.datetime.now()
    day = today.day

    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    day_pattern = re.compile(r"^\d{1,2}\s+\w{3}")

    prayer_data = []
    last_jamaah = ["N/A"] * 5  # only 5 Jama'ah slots (Fajr, Dhuhr, Asr, Maghrib, Isha)

    for line in lines:
        if not day_pattern.match(line):
            continue

        parts = line.split()
        if len(parts) < 8:
            continue

        day_num = int(parts[0])

        # Extract numeric-like parts (e.g. 5.18, 6:59, -, etc.)
        numeric_parts = [p for p in parts[2:] if re.match(r"^(\d{1,2}[:.]\d{1,2}|-)$", p)]

        # First 6 = beginning times, next up to 5 = Jama’ah
        beginning_times = numeric_parts[:6]
        jamaah_times_raw = numeric_parts[6:]

        # Ensure we have exactly 5 Jama'ah entries (pad missing with '-')
        while len(jamaah_times_raw) < 5:
            jamaah_times_raw.append("-")

        # Replace '-' with previous known time
        jamaah_times_filled = []
        for i in range(5):
            val = jamaah_times_raw[i]
            if val == '-' or val.upper() == 'N/A':
                val = last_jamaah[i]
            else:
                last_jamaah[i] = val
            jamaah_times_filled.append(val)

        prayer_data.append({
            "day": day_num,
            "begin": beginning_times,
            "jamaah": jamaah_times_filled
        })

    today_data = next((d for d in prayer_data if d["day"] == day), None)
    if not today_data:
        raise ValueError(f"Could not find timetable entry for day {day}")

    # Now align 5 Jama’ah times to 6 prayers (Sunrise has none)
    prayers = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]
    aligned_jamaah = [
        today_data["jamaah"][0],  # Fajr
        "N/A",                    # Sunrise
        today_data["jamaah"][1],  # Dhuhr
        today_data["jamaah"][2],  # Asr
        today_data["jamaah"][3],  # Maghrib
        today_data["jamaah"][4],  # Isha
    ]

    return today_data["begin"], aligned_jamaah


@app.route('/')
def index():
    # Extract prayer times
    beginning_times, jamaah_times = get_prayer_times()
    
    # Define the prayer names
    prayers = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]

    # Render the webpage with prayer times
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Prayer Times</title>
    </head>
    <body>
        <h1>Today's Prayer Times</h1>
        <table border="1">
            <thead>
                <tr>
                    <th>Prayer</th>
                    <th>Beginning Time</th>
                    <th>Jama'ah Time</th>
                </tr>
            </thead>
            <tbody>
                {% for prayer, begin, jamaah in prayer_data %}
                <tr>
                    <td>{{ prayer }}</td>
                    <td>{{ begin }}</td>
                    <td>{{ jamaah }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """

    return render_template_string(html_content, prayer_data=zip(prayers, beginning_times, jamaah_times))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

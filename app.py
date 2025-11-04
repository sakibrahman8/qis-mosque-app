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

    # Get PDF from URL
    pdf_url = get_pdf_url()
    response = requests.get(pdf_url)
    pdf_file = io.BytesIO(response.content)

    # Get today's date
    today = datetime.datetime.now()
    day = today.day

    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # We'll store parsed prayer data here
    prayer_data = []
    last_jamaah = ["N/A"] * 6  # To fill "-" with last known time

    # Regex to detect a day row (starts with date + weekday)
    day_pattern = re.compile(r"^\d{1,2}\s+\w{3}")

    # Loop through lines and pair Beginning/Jama'ah rows
    i = 0
    while i < len(lines):
        line = lines[i]

        if day_pattern.match(line):
            parts = line.split()
            if len(parts) < 8:
                i += 1
                continue  # skip incomplete rows

            day_num = int(parts[0])
            beginning_times = parts[2:8]  # Skip date + weekday

            # Assume next line = Jama’ah times (sometimes may not exist)
            jamaah_times = ["N/A"] * 6
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                jamaah_parts = next_line.split()
                if len(jamaah_parts) >= 6 and not day_pattern.match(next_line):
                    for j in range(6):
                        val = jamaah_parts[j] if j < len(jamaah_parts) else "-"
                        if val == "-" or val.upper() == "N/A":
                            val = last_jamaah[j]  # fill with last known
                        else:
                            last_jamaah[j] = val
                        jamaah_times[j] = val

            prayer_data.append({
                "day": day_num,
                "begin": beginning_times,
                "jamaah": jamaah_times
            })

        i += 1

    # Find today's row
    today_data = next((d for d in prayer_data if d["day"] == day), None)
    if not today_data:
        raise ValueError(f"Could not find timetable entry for day {day}")

    return today_data["begin"], today_data["jamaah"]

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

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

    lines = text.split('\n')
    beginning_times_line = None
    jamaah_times_line = None

    for i, line in enumerate(lines):
        if line.strip().startswith(str(day) + " "):  # e.g. "4 Mon"
            beginning_times_line = line
            if i + 1 < len(lines):
                jamaah_times_line = lines[i + 1]
            break

    if not beginning_times_line:
        raise ValueError("Could not find today's line in the timetable.")

    # Extract beginning times
    parts = beginning_times_line.strip().split()
    beginning_times = parts[2:8]  # Skip day and weekday

    # Extract jamaah times
    jamaah_parts = jamaah_times_line.strip().split() if jamaah_times_line else []
    jamaah_times = []

    for i in range(6):
        if i < len(jamaah_parts):
            t = jamaah_parts[i]
            jamaah_times.append(t if t != '-' else 'N/A')
        else:
            jamaah_times.append('N/A')

    # Insert 'N/A' for Sunrise Jama'ah
    jamaah_times[1] = 'N/A'

    return beginning_times, jamaah_times


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

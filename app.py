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

    pdf_url = get_pdf_url()
    response = requests.get(pdf_url)
    pdf_file = io.BytesIO(response.content)

    today = datetime.datetime.now()
    day = today.day

    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[0]
        table = page.extract_table()

    if not table:
        raise ValueError("Could not extract table from PDF")

    # Flatten the table rows
    rows = [r for r in table if r and any(r)]

    # Find today's row
    beginning_times = None
    jamaah_times = None

    for i, row in enumerate(rows):
        # Row example: ['4', 'Mon', '5.18', '6.59', '11.48', '2.38', '4.30', '6.00']
        if str(day) in row[0]:
            beginning_times = row[2:8]  # Fajr to Isha
            # Next row is Jama'ah times
            if i + 1 < len(rows):
                jamaah_row = rows[i + 1]
                jamaah_times = jamaah_row[1:7]  # align with Fajr to Isha
            break

    if not beginning_times:
        raise ValueError(f"Could not find today's prayer times for day {day} in PDF")

    # Clean up and fix values
    def clean_time(value):
        if not value or value.strip() == '-' or value.strip() == '':
            return 'N/A'
        return value.strip()

    beginning_times = [clean_time(v) for v in beginning_times]
    jamaah_times = [clean_time(v) for v in jamaah_times] if jamaah_times else ['N/A'] * 6

    # Sunrise has no Jama'ah time
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

from flask import Flask, render_template_string
import pdfplumber
import requests
from bs4 import BeautifulSoup
import datetime
import io
import os

app = Flask(__name__)

def get_pdf_url():
    url = 'https://quwwatulislam.org/prayertimes/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_url = soup.select_one('.post-content a').get('href')
    return pdf_url

def get_prayer_times():
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

    rows = [r for r in table if r and any(r)]
    beginning_times = None
    jamaah_times = None
    previous_jamaah_times = ['N/A'] * 6

    for i, row in enumerate(rows):
        if str(day) in (row[0] or ''):
            beginning_times = row[2:8]
            if i + 1 < len(rows):
                jamaah_row = rows[i + 1]
                jamaah_times = []
                for j, val in enumerate(jamaah_row[1:7]):
                    if val.strip() == '"':
                        jamaah_times.append(previous_jamaah_times[j])
                    elif val.strip() in ('', '-'):
                        jamaah_times.append('N/A')
                    else:
                        jamaah_times.append(val.strip())
                        previous_jamaah_times[j] = val.strip()
            break
        elif i + 1 < len(rows):
            jamaah_row = rows[i + 1]
            for j, val in enumerate(jamaah_row[1:7]):
                if val and val.strip() != '"':
                    previous_jamaah_times[j] = val.strip()

    if not beginning_times:
        raise ValueError(f"Could not find today's prayer times for day {day} in PDF")

    def clean_time(v):
        return v.strip() if v and v.strip() not in ('', '-') else 'N/A'

    beginning_times = [clean_time(v) for v in beginning_times]
    jamaah_times = jamaah_times if jamaah_times else ['N/A'] * 6
    jamaah_times[1] = 'N/A'  # Sunrise has no Jama'ah time

    return beginning_times, jamaah_times

@app.route('/')
def index():
    beginning_times, jamaah_times = get_prayer_times()
    prayers = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]

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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

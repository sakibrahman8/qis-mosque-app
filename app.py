from flask import Flask, render_template_string
import pdfplumber
import requests
from bs4 import BeautifulSoup
import datetime
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

    with open('prayer_times.pdf', 'wb') as f:
        f.write(response.content)

    today = datetime.datetime.now()
    day = str(today.day)

    beginning_times = ['-'] * 6
    jamaah_times = ['N/A'] * 6
    previous_jamaah = [""] * 6

    with pdfplumber.open("prayer_times.pdf") as pdf:
        page = pdf.pages[0]
        table = page.extract_table()

        for row in table:
            if row and row[0] and day in row[0].strip():
                # Extract columns safely
                raw = [r.strip() if r else "" for r in row]

                # Beginning times: [Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha]
                beginning_times = raw[2:8]

                # Jama'ah times start at column 8
                for i, jt in enumerate(raw[8:14]):
                    if i == 1:
                        jamaah_times[i] = "N/A"  # Sunrise
                    elif jt == '"':
                        jamaah_times[i] = previous_jamaah[i] or "N/A"
                    else:
                        jamaah_times[i] = jt
                        previous_jamaah[i] = jt
                break

    return beginning_times, jamaah_times

@app.route('/')
def index():
    beginning_times, jamaah_times = get_prayer_times()
    prayers = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prayer Times</title>
        <style>
            body {
                font-family: Arial, sans-serif;
            }
            h1 {
                font-size: 2em;
            }
            table {
                border-collapse: collapse;
                width: 50%;
            }
            th, td {
                border: 1px solid black;
                padding: 8px 12px;
                text-align: center;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h1>Today's Prayer Times</h1>
        <table>
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

    return render_template_string(html, prayer_data=zip(prayers, beginning_times, jamaah_times))

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

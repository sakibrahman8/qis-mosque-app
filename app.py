from flask import Flask, render_template_string
import pdfplumber
import requests
from bs4 import BeautifulSoup
import datetime
import os
import io

app = Flask(__name__)

def get_pdf_url():
    url = 'https://quwwatulislam.org/prayertimes/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_link = soup.select_one('.post-content a')
    return pdf_link.get('href') if pdf_link else None

def get_prayer_times():
    pdf_url = get_pdf_url()
    if not pdf_url:
        raise ValueError("Could not find PDF link on the site.")

    response = requests.get(pdf_url)
    if response.status_code != 200:
        raise ValueError("Failed to download the timetable PDF.")

    # Load PDF into memory
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        page = pdf.pages[0]
        table = page.extract_table()

    today = datetime.datetime.now()
    day = today.day

    beginning_times = []
    jamaah_times = []
    previous_jamaah = ['N/A'] * 6  # To track previous values

    for row in table:
        if row and row[0] and str(day) in str(row[0]):
            # Extract relevant cells: [0]=Day, [1]=Fajr, ..., [6]=Isha
            beginning_times = row[1:7]

            # Jama'ah times usually follow in [7:] but some cells may be missing or contain '"'
            raw_jamaah = row[7:]
            for i in range(6):
                if i == 1:
                    jamaah_times.append("N/A")  # Sunrise has no Jama'ah
                elif i < len(raw_jamaah):
                    time = raw_jamaah[i]
                    if time == '"' or not time:
                        jamaah_times.append(previous_jamaah[i])
                    else:
                        jamaah_times.append(time)
                        previous_jamaah[i] = time
                else:
                    jamaah_times.append(previous_jamaah[i])
            break

    # Handle missing data
    if not beginning_times:
        beginning_times = ["-"] * 6
    if not jamaah_times:
        jamaah_times = ["N/A"] * 6
    elif len(jamaah_times) < 6:
        jamaah_times += ["N/A"] * (6 - len(jamaah_times))

    return beginning_times, jamaah_times

@app.route('/')
def index():
    try:
        beginning_times, jamaah_times = get_prayer_times()
    except Exception as e:
        return f"<h1>Error fetching prayer times</h1><pre>{str(e)}</pre>"

    prayers = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prayer Times</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            h1 { font-size: 2em; }
            table { border-collapse: collapse; width: 50%; }
            th, td { border: 1px solid #000; padding: 8px; text-align: center; }
            th { background-color: #eee; }
        </style>
    </head>
    <body>
        <h1>Today's Prayer Times</h1>
        <table>
            <tr><th>Prayer</th><th>Beginning Time</th><th>Jama'ah Time</th></tr>
            {% for prayer, begin, jamaah in prayer_data %}
            <tr>
                <td>{{ prayer }}</td>
                <td>{{ begin }}</td>
                <td>{{ jamaah }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_content, prayer_data=zip(prayers, beginning_times, jamaah_times))

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

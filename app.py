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
    # Get the latest PDF URL
    pdf_url = get_pdf_url()
    
    # Download the PDF
    response = requests.get(pdf_url)
    
    # Save the PDF temporarily
    with open('prayer_times.pdf', 'wb') as f:
        f.write(response.content)

    # Open the PDF and extract text
    with pdfplumber.open('prayer_times.pdf') as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
    
    # Get today's date
    today = datetime.datetime.now()
    day = today.day

    # Store previous jama'ah times for the case of ""
    previous_jamaah_times = ['N/A'] * 5

    # Extract today's prayer times
    beginning_times = []
    jamaah_times = []
    for line in text.split('\n'):
        if line.startswith(str(day) + " "):  # Find the line starting with today's date
            # Split the line into beginning times and jama'ah times using '|'
            prayer_times = line.split('|')
            beginning_times = prayer_times[0].split()[2:8]  # Get Fajr to Isha
            
            # Process Jama'ah times
            raw_jamaah_times = prayer_times[1].split()
            for i, time in enumerate(raw_jamaah_times):
                if time == '"':
                    jamaah_times.append(previous_jamaah_times[i])
                else:
                    jamaah_times.append(time)
                    previous_jamaah_times[i] = time
            break
        else:
            # Update previous_jamaah_times if the row contains times
            if '|' in line:
                _, raw_jamaah_times = line.split('|')
                for i, time in enumerate(raw_jamaah_times.split()):
                    if time != '"':
                        previous_jamaah_times[i] = time

    # Add N/A for sunrise and any missing Jama'ah times
    if not jamaah_times or len(jamaah_times) < 5:
        jamaah_times = [jamaah_times[i] if i != 1 else 'N/A' for i in range(5)]  # 'N/A' for Sunrise
    else:
        jamaah_times.insert(1, 'N/A')  # Insert 'N/A' for Sunrise

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

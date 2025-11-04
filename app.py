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
    response = requests.get(pdf_url)
    
    # Use in‑memory PDF rather than writing to disk (better for Heroku)
    import io
    pdf_file = io.BytesIO(response.content)
    
    # Open the PDF and extract text
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
    
    today = datetime.datetime.now()
    day = today.day
    
    previous_jamaah_times = ['N/A'] * 6  # Keep for fallback (6‑slots inc Sunrise slot)
    beginning_times = None
    jamaah_times = None
    
    for line in text.split('\n'):
        line = line.strip()
        # Attempt to find a row starting with the day number
        if line.startswith(f"{day} ") or line.startswith(f"{day}\t") or line.startswith(f"{day} "):
            # Found the relevant line
            # Now attempt to split into “beginning” part and “jama’ah” part
            if '|' in line:
                parts = line.split('|')
            else:
                # fallback: maybe new format uses some other delimiter, try split on double‑space
                parts = line.split('  ')
            
            # Beginning times part
            begin_part = parts[0].split()
            # Determine the slice for beginning times:
            # e.g., if format is: Day, (maybe DayName), Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha
            # So attempt to drop first 2 items then next 6
            if len(begin_part) >= 8:
                beginning_times = begin_part[-6:]  # take the last 6 entries
            else:
                beginning_times = begin_part[2:8]  # fallback slice
            
            # Jama’ah part (if exists)
            if len(parts) > 1:
                raw_jamaah = parts[1].split()
            else:
                raw_jamaah = []
            
            jamaah_times = []
            for i in range(6):
                # For each of Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha
                if i < len(raw_jamaah):
                    t = raw_jamaah[i]
                    if t in ('"', '—', ''):
                        jamaah_times.append(previous_jamaah_times[i])
                    else:
                        jamaah_times.append(t)
                        previous_jamaah_times[i] = t
                else:
                    jamaah_times.append(previous_jamaah_times[i])
            
            break
        else:
            # update previous_jamaah_times from earlier rows if they have valid times
            if '|' in line:
                try:
                    parts2 = line.split('|')
                    raw2 = parts2[1].split()
                    for i, t2 in enumerate(raw2):
                        if t2 not in ('"', '—', ''):
                            previous_jamaah_times[i] = t2
                except:
                    pass
    
    if beginning_times is None or jamaah_times is None:
        raise ValueError("Could not find today's prayer times in the PDF. Day:", day)
    
    # Sunrise slot: Jama’ah time likely not applicable => set to 'N/A'
    # we assume index 1 corresponds to Sunrise
    jamaah_times[1] = 'N/A'
    
    # Ensure lists have exactly 6 entries
    if len(beginning_times) != 6:
        # If it has less, pad or raise
        beginning_times = (beginning_times + ['N/A']*6)[:6]
    if len(jamaah_times) != 6:
        jamaah_times = (jamaah_times + ['N/A']*6)[:6]
    
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

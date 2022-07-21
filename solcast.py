import requests
import json
import csv
import os
import datetime
import pandas as pd
import glob
import matplotlib.pyplot as plt
import matplotlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path


PATH = "/home/debian/solar-test/"
SITES_FILENAME = PATH + 'sites.json'
BASE_URL = "https://api.solcast.com.au/"


def forecasts_to_csv(json_file, csv_filename):
    """Save JSON object as CSV file. Expects JSON to be output from world API call"""
    
    with open(json_file) as json_input:
        data = json.load(json_input)
    
    with open(csv_filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')

        csvwriter.writerow(['Period End', 'GHI', 'GHI 90', 'GHI 10', 'Period']) # Header
        for entry in data['forecasts']:
            ghi = entry['ghi']
            ghi90 = entry['ghi90']
            ghi10 = entry['ghi10']
            period_end = entry['period_end']
            period = entry['period']
            csvwriter.writerow([period_end, ghi, ghi90, ghi10, period])


def actuals_to_csv(json_file, csv_filename):
    """Save JSON object as CSV file. Expects JSON to be output from world API call"""
    
    with open(json_file) as json_input:
        data = json.load(json_input)
    
    with open(csv_filename, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')

        csvwriter.writerow(['Period End', 'GHI', 'Period']) # Header
        for entry in data['estimated_actuals']:
            ghi = entry['ghi']
            period_end = entry['period_end']
            period = entry['period']
            csvwriter.writerow([period_end, ghi, period])


class Site:
    """
    
    """

    def __init__(self, id=1, name="", latitude="", longitude="", api_key="", timezone=0, client_name="", auto=True):

        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.api_key = api_key
        self.timezone = timezone
        self.client_name = client_name

        # Read data from sites.json
        if auto:
            with open(SITES_FILENAME, 'r') as sites_file:
                sites_dict = json.load(sites_file)
            site = {}
            for entry in sites_dict['sites']:
                if entry['id'] == self.id:
                    site = entry
                    break
            
            if site:
                self.name = site['name']
                self.latitude = site['latitude']
                self.longitude = site['longitude']
                self.api_key = site['API_key']
                self.timezone = site['timezone']
                self.client_name = site['client_name']
            else:
                return # No site found in db!
        
        # Ensure folder exists
        if not os.path.isdir(f'{PATH}sites/{self.id}'):
            os.makedirs(f'{PATH}sites/{self.id}')

    def get_forecast(self, hours=48):
        """Get a site's forecast and save as .csv"""
        
        endpoint = "world_radiation/forecasts.json"
        url = BASE_URL + endpoint
        
        response = requests.get(url, auth=(self.api_key, ''), params={'latitude': self.latitude, 'longitude': self.longitude})
        response.raise_for_status()

        json_data = response.json()
        now = datetime.datetime.now()
        csv_filename = f"{self.id}_forecast_{now.year}_{now.month}_{now.day}_{now.hour}.csv"
        with open(f'{PATH}sites/{self.id}/{csv_filename}', 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')

            csvwriter.writerow(['Period End', 'GHI', 'GHI 90', 'GHI 10', 'Period']) # Header
            for entry in json_data['forecasts']:
                ghi = entry['ghi']
                ghi90 = entry['ghi90']
                ghi10 = entry['ghi10']
                period_end = entry['period_end']
                period = entry['period']
                csvwriter.writerow([period_end, ghi, ghi90, ghi10, period])

    def get_actuals(self):
        """Get a site's estimated actuals and save as .csv"""
        
        endpoint = "world_radiation/estimated_actuals.json"
        url = BASE_URL + endpoint
        
        response = requests.get(url, auth=(self.api_key, ''), params={'latitude': self.latitude, 'longitude': self.longitude})
        response.raise_for_status()

        json_data = response.json()
        now = datetime.datetime.now()
        csv_filename = f"{self.id}_actuals_{now.year}_{now.month}_{now.day}_{now.hour}.csv"
        with open(f'{PATH}sites/{self.id}/{csv_filename}', 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')

            csvwriter.writerow(['Period End', 'GHI', 'Period']) # Header
            for entry in json_data['estimated_actuals']:
                ghi = entry['ghi']
                period_end = entry['period_end']
                period = entry['period']
                csvwriter.writerow([period_end, ghi, period])

    def create_plots(self):
        """Create and save historical and forecasted irradiance plots for the site."""

        # Get latest data
        list_of_files = glob.glob(f'{PATH}sites/{self.id}/*.csv')
        actuals = max([f for f in list_of_files if "actual" in f], key=os.path.getctime) # Get latest actuals
        forecasts = max([f for f in list_of_files if "forecast" in f], key=os.path.getctime)

        # Move into df, update times
        actuals_df = pd.read_csv(actuals)
        forecasts_df = pd.read_csv(forecasts)

        actuals_df['Period End'] = pd.to_datetime(actuals_df["Period End"], yearfirst=True)
        actuals_df['Period End'] = actuals_df['Period End'] + pd.Timedelta(hours=self.timezone)
        forecasts_df['Period End'] = pd.to_datetime(forecasts_df["Period End"], yearfirst=True)
        forecasts_df['Period End'] = forecasts_df['Period End'] + pd.Timedelta(hours=self.timezone)

        # Sort
        actuals_df.sort_values(by='Period End', inplace=True)
        forecasts_df.sort_values(by='Period End', inplace=True)

        # Plotting
        now_str = str(datetime.datetime.now().date())
        matplotlib.style.use('fivethirtyeight')
        font = {'family' : 'normal',
                'weight' : 'normal',
                'size'   : 22}
        plt.rc('font', **font)

        # Forecast graph
        x = forecasts_df['Period End']
        y = forecasts_df['GHI']
        fig = plt.figure(figsize = (20, 10))
        plt.plot(x, y)
        plt.title(f"Forecast for {self.name}\n{now_str}")
        plt.ylabel("W/m^2")
        plt.savefig(f'{PATH}sites/{self.id}/forecast.png')

        # Actuals graph
        x = actuals_df['Period End']
        y = actuals_df['GHI']
        fig = plt.figure(figsize = (20, 10))
        plt.plot(x, y)
        plt.title(f"Irradiance for {self.name}\n{now_str}")
        plt.ylabel("W/m^2")
        plt.savefig(f'{PATH}sites/{self.id}/actuals.png')
    
    def send_demo_report(self, debug=False):
        """Send a demo report via email for the site."""

        sender = "N/A"
        recipients = ['N/A', 'N/A']
        app_pw = "N/A" # Email API key

        # Connect to SMTP
        server = smtplib.SMTP_SSL('smtp.fastmail.com', port=465)
        server.login(sender, app_pw)

        # Debug
        if debug:
            server.set_debuglevel(1)

        # Create message
        msg = MIMEMultipart('related')
        now_str = str(datetime.datetime.now().date())
        msg['Subject'] = f'Daily Solar Report {now_str}'
        msg['From'] = sender
        msg['To'] = ", ".join(recipients)

        # HTML
        html = f"""\
        <html>
        <div style="max-width:600px;background-color:azure">
            <header style="background-color: #008cba; color:white; text-align: center; padding: 1px;font-family: 'Open Sans', sans-serif">
            <h1 style="font-family: 'Open Sans', sans-serif">Daily Solar Report</h1>
            </header>
            <body>
            <p style="font-family: 'Open Sans', sans-serif">Good morning {self.client_name},</p>
            <p style="font-family: 'Open Sans', sans-serif">
                Yesterday, your system performed <span style="color:rgb(79, 128, 30)"><i>well</i></span>.<br><br>
                <table style="margin-left:auto;margin-right: auto;text-align:center;border: 1px solid black;">
                    <tr>
                        <th style="width: 140px">Solar Production</th>
                        <th style="width: 140px">Consumption</th>
                        <th style="width: 140px">Import</th>
                        <th style="width: 140px">Export</th>
                    </tr>
                    <tr>
                        <td>6 kWh</td>
                        <td>9.4 kWh</td>
                        <td>3.6 kWh</td>
                        <td>0.2 kWh</td>
                    </tr>
                </table><br>
                <div style="text-align: center;font-family: 'Open Sans', sans-serif"><h3>Yesterday's Production:</h3></span>
                <table width="100%" style="max-width:600px;">
                    <tr>
                    <td>
                        <img src="cid:image1" width="100%" />
                    </td>
                    </tr>
                </table><br>
            </p>
            <p style="font-family: 'Open Sans', sans-serif">
                <div style="text-align: center;font-family: 'Open Sans', sans-serif"><h3>Today's Forecast:</h3></span>
                <table width="100%" style="max-width:600px;">
                    <tr>
                    <td>
                        <img src="cid:image2" width="100%" />
                    </td>
                    </tr>
                </table><br><br>
            </p>
            <p style="font-family: 'Open Sans', sans-serif">
                <b>© 2020 Traverse Technologies, All rights reserved.</b><br>
                <a href="www.traverse.com.au">www.traverse.com.au</a>
                <div style="display:flex; flex-direction:row;justify-content: space-evenly;">
                    <div><b>Australia</b><br>+61 3 9489 6678<br>160 Holden Street, Fitzroy North<br>Victoria 3068, Melbourne, Australia</div>
                    <div><b>New Zealand</b><br>+64 9 884 9756<br>Unit 5B / 5 Douglas Alexander Parade<br>Rosedale, Auckland 0623, New Zealand</div>
                </div>
            </p>
            </body>
        </div>
        </html>
        """

        # Record the MIME types of text/html.
        part2 = MIMEText(html, 'html')

        # Attach parts into message container.
        msg.attach(part2)

        # Embed images
        with open(f'{PATH}sites/{self.id}/actuals.png', 'rb') as fp:
            msgImage = MIMEImage(fp.read())
        msgImage.add_header('Content-ID', '<image1>')
        msg.attach(msgImage)
        with open(f'{PATH}sites/{self.id}/forecast.png', 'rb') as fp:
            msgImage = MIMEImage(fp.read())
        msgImage.add_header('Content-ID', '<image2>')
        msg.attach(msgImage)

        # Send it
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()
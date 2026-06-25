import gspread
import pandas as pd
import requests
import zipfile
import io
import json
import os

from datetime import datetime, timedelta

from oauth2client.service_account import ServiceAccountCredentials


# ----------------------------
# GOOGLE SHEETS LOGIN
# ----------------------------

creds_json = os.environ["GCP_CREDENTIALS"]

creds = json.loads(creds_json)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    creds,
    scope
)

client = gspread.authorize(credentials)

SPREADSHEET_ID = "1SIZ5uhesUd6sC4DyvpBetQDYS3sIe6iWHVIfF8hRIOM"

top_sheet = client.open_by_key(
    SPREADSHEET_ID
).worksheet("Top 250 Stocks")

final_sheet = client.open_by_key(
    SPREADSHEET_ID
).worksheet("Final list")
# ----------------------------
# DOWNLOAD NSE BHAVCOPY
# ----------------------------

def fetch_bhavcopy(date_obj):

    date_str = date_obj.strftime("%Y%m%d")

    url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        return None

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:

        csv_file = z.namelist()[0]

        with z.open(csv_file) as f:

            df = pd.read_csv(f)

    return df
    # ----------------------------
# FIND LATEST TRADING DAY
# ----------------------------

df = None

for i in range(5):

    d = datetime.now() - timedelta(days=i)

    if d.weekday() >= 5:
        continue

    df = fetch_bhavcopy(d)

    if df is not None:
        break

if df is None:
    raise Exception("Bhavcopy Not Found")

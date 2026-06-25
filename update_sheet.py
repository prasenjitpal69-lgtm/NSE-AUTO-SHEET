import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import requests
import zipfile
import io
from datetime import datetime, timedelta
import os
import json

# -----------------------------
# Google Credentials
# -----------------------------
creds_json = os.environ.get("GCP_CREDENTIALS")
creds_dict = json.loads(creds_json)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1SIZ5uhesUd6sC4DyvpBetQDYS3sIe6iWHVIfF8hRIOM"

spreadsheet = client.open_by_key(SPREADSHEET_ID)

worksheet = spreadsheet.worksheet("Top 250 Stocks")

# -----------------------------
# Fetch NSE Bhavcopy
# -----------------------------
def fetch_bhavcopy_for_date(date_obj):

    date_str = date_obj.strftime("%Y%m%d")

    url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code != 200:
            return None

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:

            csv_file = z.namelist()[0]

            with z.open(csv_file) as f:

                df = pd.read_csv(f)

        symbol_col = "TckrSymb" if "TckrSymb" in df.columns else "SYMBOL"
        close_col = "ClsPric" if "ClsPric" in df.columns else "CLOSE"
        series_col = "SctySrs" if "SctySrs" in df.columns else "SERIES"

        volume_col = None

        for c in [
            "TtlTradgVol",
            "TtlTrdQty",
            "TotTrdQty",
            "TOTTRDQTY"
        ]:
            if c in df.columns:
                volume_col = c
                break

        if volume_col is None:
            return None

        df = df[df[series_col].astype(str).str.strip() == "EQ"]

        df = df[
            ~df[symbol_col].astype(str).str.contains(
                "ETF|BEES|LIQUID|GOLD|SILVER|CASE",
                case=False,
                na=False
            )
        ]

        df = df.sort_values(
            by=volume_col,
            ascending=False
        ).head(250)

        return df[[symbol_col, volume_col, close_col]].values.tolist()

    except Exception as e:

        print(e)

        return None


# -----------------------------
# Get Latest Trading Day
# -----------------------------
today = datetime.now()

data_to_insert = None

fetched_date = ""

for i in range(5):

    d = today - timedelta(days=i)

    if d.weekday() >= 5:
        continue

    data_to_insert = fetch_bhavcopy_for_date(d)

    if data_to_insert:

        fetched_date = d.strftime("%d-%b-%Y")

        break


# -----------------------------
# Update Top250 Sheet
# -----------------------------
if data_to_insert:

    worksheet.batch_clear(["A2:C251"])

    worksheet.update("A2", data_to_insert)

    ist = (
        datetime.utcnow() +
        timedelta(hours=5, minutes=30)
    ).strftime("%d-%b %H:%M")

    worksheet.update(
        "K2",
        [[
            f"Data Date: {fetched_date} | Last Update: {ist} (IST)"
        ]]
    )

    print("Top 250 Updated")


# -----------------------------
# Update Final List Sheet
# -----------------------------
try:

    final_sheet = spreadsheet.worksheet("Final list")

    final_sheet.batch_clear(["A2:H1000"])

    rows = []

    for row in data_to_insert:

        rows.append([

            row[0],      # NSE CODE

            row[2],      # CMP

            row[1],      # VOLUME

            "",

            "",

            "",

            "",

            ""

        ])

    if rows:

        final_sheet.update("A2", rows)

    print("Final List Updated")

except Exception as e:

    print("Final List Error")

    print(e)

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
if df is None:
    raise Exception("Bhavcopy Not Found")

# -----------------------------
# FILTER TOP 250
# -----------------------------
symbol_col = "TckrSymb" if "TckrSymb" in df.columns else "SYMBOL"
close_col = "ClsPric" if "ClsPric" in df.columns else "CLOSE"
series_col = "SctySrs" if "SctySrs" in df.columns else "SERIES"

volume_col = None

for c in ["TtlTradgVol", "TtlTrdQty", "TotTrdQty", "TOTTRDQTY"]:
    if c in df.columns:
        volume_col = c
        break

if volume_col is None:
    raise Exception("Volume column not found")

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

data_to_insert = df[[symbol_col, volume_col, close_col]].values.tolist()

# -----------------------------
# UPDATE TOP 250
# -----------------------------
top_sheet.batch_clear(["A2:C251"])
top_sheet.update("A2", data_to_insert)

print("Top 250 Updated")

# -----------------------------
# UPDATE FINAL LIST
# -----------------------------
final_sheet.batch_clear(["A2:H1000"])

rows = []

for row in data_to_insert:
    rows.append([
        row[0],
        row[2],
        row[1],
        "",
        "",
        "",
        "",
        ""
    ])

final_sheet.update("A2", rows)

print("Final List Updated")

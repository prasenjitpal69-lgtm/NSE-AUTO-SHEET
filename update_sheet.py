import os
import json
import requests
import zipfile
import io
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

def update_sheets():
    try:
        # 1. Login to Google Sheets using environment variable
        creds_json = os.environ.get("GCP_CREDENTIALS")
        if not creds_json:
            raise ValueError("GCP_CREDENTIALS environment variable not set")
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # 2. Open Spreadsheet by Key
        spreadsheet_id = "1SIZ5uhesUd6sC4DyvpBetQDYS3sIe6iWHVIfF8hRIOM"
        spreadsheet = client.open_by_key(spreadsheet_id)

        # 3. Detect latest trading day and download NSE Bhavcopy
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        
        bhav_df = None
        data_date_str = ""
        current_date = datetime.now()
        
        # Search last 10 days for the latest file
        for i in range(10):
            check_date = current_date - timedelta(days=i)
            if check_date.weekday() >= 5: # Skip weekends
                continue
                
            date_str = check_date.strftime("%Y%m%d")
            url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"
            
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        csv_filename = z.namelist()[0]
                        with z.open(csv_filename) as f:
                            bhav_df = pd.read_csv(f)
                            # Clean column names (strip whitespace)
                            bhav_df.columns = bhav_df.columns.str.strip()
                            data_date_str = check_date.strftime("%Y-%m-%d")
                    break
            except Exception:
                continue

        if bhav_df is None:
            raise Exception("Could not download NSE Bhavcopy.")

        # 4. Process Data
        # Filter EQ series
        df = bhav_df[bhav_df['SERIES'] == 'EQ'].copy()

        # Remove ETF, BEES, GOLD, SILVER, LIQUID
        exclude_list = ['ETF', 'BEES', 'GOLD', 'SILVER', 'LIQUID']
        pattern = '|'.join(exclude_list)
        df = df[~df['SYMBOL'].str.contains(pattern, case=False, na=False)]

        # Sort by volume and take top 250
        df = df.sort_values(by='TOTTRDQTY', ascending=False)
        top_250 = df.head(250).copy()

        # Get timestamps for K2
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_info = f"Data Date: {data_date_str} | Updated: {now_str}"

        # 5. Update "Top 250 Stocks"
        sheet_top = spreadsheet.worksheet("Top 250 Stocks")
        sheet_top.batch_clear(["A2:C251"])
        
        # Prepare: Symbol, Volume, Close Price
        top_250_data = top_250[['SYMBOL', 'TOTTRDQTY', 'CLOSE']].values.tolist()
        sheet_top.update('A2', top_250_data)
        sheet_top.update('K2', [[update_info]])
        print("Top 250 Updated")

        # 6. Update "Final list"
        sheet_final = spreadsheet.worksheet("Final list")
        sheet_final.batch_clear(["A2:H1000"])
        
        # Column A=Symbol, B=Close, C=Volume, D:H=Blank
        final_list_df = top_250[['SYMBOL', 'CLOSE', 'TOTTRDQTY']].copy()
        for i in range(5):
            final_list_df[f'blank_{i}'] = ""
            
        final_list_data = final_list_df.values.tolist()
        sheet_final.update('A2', final_list_data)
        sheet_final.update('K2', [[update_info]])
        print("Final List Updated")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_sheets()

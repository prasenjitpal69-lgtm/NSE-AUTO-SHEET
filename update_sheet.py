import os
import json
import requests
import zipfile
import io
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from datetime import timedelta

def main():
    client = None
    try:
        # 1. Authentication
        creds_json = os.environ.get("GCP_CREDENTIALS")
        if not creds_json:
            print("Error: GCP_CREDENTIALS environment variable is not set.")
            return

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(creds_json)
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # 2. Define client before accessing worksheets
        client = gspread.authorize(credentials)
        print("Authenticated with Google Sheets successfully.")

        # 3. Open Spreadsheet by Key
        spreadsheet_id = "1SIZ5uhesUd6sC4DyvpBetQDYS3sIe6iWHVIfF8hRIOM"
        spreadsheet = client.open_by_key(spreadsheet_id)

        # 4. Download latest NSE Bhavcopy from NSE Archives
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://www.nseindia.com/"
        }
        
        bhav_df = None
        data_date_str = ""
        
        # Search last 10 trading days for the latest available file
        for i in range(10):
            check_date = datetime.now() - timedelta(days=i)
            if check_date.weekday() >= 5: # Skip Saturday and Sunday
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
                            # Cleanup column names to remove leading/trailing spaces
                            bhav_df.columns = bhav_df.columns.str.strip()
                            data_date_str = check_date.strftime("%d-%m-%Y")
                    print(f"Successfully downloaded Bhavcopy for {data_date_str}")
                    break
            except Exception as e:
                print(f"Bhavcopy check for {date_str} failed or unavailable: {e}")
                continue

        if bhav_df is None:
            print("Error: Could not find any valid NSE Bhavcopy in the last 10 trading days.")
            return

        # 5. Process Data
        # Requirement: Keep only SERIES == EQ
        df = bhav_df[bhav_df['SERIES'] == 'EQ'].copy()
        
        # Requirement: Remove all ETF, BEES, GOLD, SILVER, LIQUID symbols
        exclude_keywords = ['ETF', 'BEES', 'GOLD', 'SILVER', 'LIQUID']
        pattern = '|'.join(exclude_keywords)
        df = df[~df['SYMBOL'].str.contains(pattern, case=False, na=False)]
        
        # Requirement: Sort by TOTTRDQTY descending and take top 250
        df = df.sort_values(by='TOTTRDQTY', ascending=False)
        top_250 = df.head(250).copy()

        # Generate timestamps
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_msg = f"Data Date: {data_date_str} | Updated: {now_ts}"

        # 6. Update Worksheet: Top 250 Stocks
        # Columns: A:SYMBOL, B:TOTTRDQTY, C:CLOSE
        ws_top = spreadsheet.worksheet("Top 250 Stocks")
        # Clear existing data from A2 downwards to ensure fresh write
        ws_top.batch_clear(["A2:C500"])
        
        top_data = top_250[['SYMBOL', 'TOTTRDQTY', 'CLOSE']].values.tolist()
        # Requirement: Use latest gspread syntax worksheet.update(range_name=..., values=...)
        ws_top.update(range_name="A2", values=top_data)
        # Requirement: Write update timestamp into K2
        ws_top.update(range_name="K2", values=[[status_msg]])
        print("Top 250 Updated")

        # 7. Update Worksheet: Final list
        # Columns: A:SYMBOL, B:CLOSE, C:TOTTRDQTY, D:H:blank
        ws_final = spreadsheet.worksheet("Final list")
        # Clear existing data from A2 downwards
        ws_final.batch_clear(["A2:H1000"])
        
        final_list_df = top_250[['SYMBOL', 'CLOSE', 'TOTTRDQTY']].copy()
        # Add 5 blank columns (D:H)
        for i in range(5):
            final_list_df[f'blank_{i}'] = ""
            
        final_data = final_list_df.values.tolist()
        # Requirement: Use latest gspread syntax worksheet.update(range_name=..., values=...)
        ws_final.update(range_name="A2", values=final_data)
        # Requirement: Write update timestamp into K2
        ws_final.update(range_name="K2", values=[[status_msg]])
        print("Final List Updated")

    except Exception as e:
        print(f"An error occurred during script execution: {str(e)}")

if __name__ == "__main__":
    main()

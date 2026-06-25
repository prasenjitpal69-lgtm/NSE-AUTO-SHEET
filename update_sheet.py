name: Update NSE Stocks

on:
  schedule:
    - cron: '30 13 * * 1-5' # Runs at 7:00 PM IST Mon-Fri
  workflow_dispatch: # Allows manual run

jobs:
  update-sheet:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pandas requests gspread oauth2client

      - name: Run Python Script
        env:
          GCP_CREDENTIALS: ${{ secrets.GCP_CREDENTIALS }}
        run: python update_sheet.py

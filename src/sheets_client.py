import gspread

class SheetsClient:
    def __init__(self, service_account_path, sheet_name):
        # Authenticate using the JSON key
        self.gc = gspread.service_account(filename=service_account_path)
        self.sh = self.gc.open(sheet_name)
        self.worksheet = self.sh.get_worksheet(0)

    def append_daily_row(self, data):
        # Prepare the row list in the order you want them in the sheet
        row = [
            data["date"],
            data["steps"],
            data["resting_hr"],
            data["stress"],
            data["hydration"],
            data["activity"]
        ]
        self.worksheet.append_row(row)
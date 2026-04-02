import gspread

class SheetsClient:
    def __init__(self, service_account_path, sheet_name):
        self.gc = gspread.service_account(filename=service_account_path)
        self.sh = self.gc.open(sheet_name)

    def sync_to_tab(self, tab_name, data, headers, is_list=False):
        # 1. Get or Create the Tab
        try:
            worksheet = self.sh.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            worksheet = self.sh.add_worksheet(title=tab_name, rows="100", cols=str(len(headers) + 5))

        # 2. Check for Headers
        first_row = worksheet.row_values(1)
        if not first_row:
            print(f"📝 Tab '{tab_name}' is empty. Adding headers...")
            worksheet.append_row(headers)

        # 3. Append the Data
        if is_list:
            if data: # Only append if the list isn't empty
                worksheet.append_rows(data)
        else:
            worksheet.append_row(data)
import gspread
import json

class SheetsClient:
    def __init__(self, service_account_path, sheet_name):
        self.gc = gspread.service_account(filename=service_account_path)
        self.sh = self.gc.open(sheet_name) # This is self.sh

    def sync_to_tab(self, tab_name, data, headers, is_list=False):
        """Syncs data to a tab. Appends if it's a list (Raw), Updates/Appends if it's a row (Log)."""
        try:
            worksheet = self.sh.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            worksheet = self.sh.add_worksheet(title=tab_name, rows="1000", cols=str(len(headers) + 5))

        # 1. Ensure Headers exist
        first_row = worksheet.row_values(1)
        if not first_row:
            worksheet.append_row(headers)
            first_row = headers

        # 2. Append Logic
        if is_list:
            # For Raw logs, we just keep appending every entry
            if data:
                worksheet.append_rows(data)
        else:
            # For Wide logs (Daily_Master, Lifestyle_Log), we want ONE row per date
            target_date = data[0] # Assuming first column is always Date
            all_dates = worksheet.col_values(1)
            
            if target_date in all_dates:
                # Find the row index (1-based) and update it
                row_idx = all_dates.index(target_date) + 1
                # Update the specific row range (A to whatever the end column is)
                end_col = gspread.utils.rowcol_to_a1(1, len(data)).split('1')[0]
                worksheet.update(f"A{row_idx}:{end_col}{row_idx}", [data])
                print(f"🔄 Updated existing row for {target_date} in {tab_name}")
            else:
                # Date not found, append a new row
                worksheet.append_row(data)
                print(f"➕ Added new row for {target_date} in {tab_name}")

    def process_lifestyle_logs(self, target_date):
        """Pivots data from Lifestyle_Raw to a wide-format Lifestyle_Log."""
        print(f"📊 Pivoting lifestyle data for {target_date}...")
        
        # 1. Fetch raw data (Fixed self.sh)
        raw_ws = self.sh.worksheet("Lifestyle_Raw")
        raw_rows = raw_ws.get_all_records()
        
        # 2. Extract values into a dictionary
        daily_map = {"Date": target_date}
        for row in raw_rows:
            if str(row['Date']) == target_date:
                name = row['Behavior Name']
                status = row['Status']
                
                val = status
                try:
                    # Clean up the details string to get the number
                    details = json.loads(row['Details'])
                    if details and isinstance(details, list) and 'amount' in details[0]:
                        val = details[0]['amount']
                except:
                    pass
                
                daily_map[name] = val

        if len(daily_map) <= 1:
            print(f"Empty raw data for {target_date}, skipping pivot.")
            return

        # 3. Get/Create the Lifestyle_Log sheet (Fixed self.sh)
        try:
            log_ws = self.sh.worksheet("Lifestyle_Log")
        except gspread.WorksheetNotFound:
            log_ws = self.sh.add_worksheet(title="Lifestyle_Log", rows="1000", cols="20")
            log_ws.update('A1', [['Date']])

        # 4. Sync Headers (Top Row)
        existing_headers = log_ws.row_values(1)
        new_columns = [col for col in daily_map.keys() if col not in existing_headers]
        
        if new_columns:
            print(f"✨ New behaviors detected! Adding columns: {new_columns}")
            existing_headers = existing_headers + new_columns
            log_ws.update('A1', [existing_headers])

        # 5. Prepare the data row in the correct column order
        # We use "NO" or 0 as default if a specific behavior wasn't logged that day
        final_row = [daily_map.get(header, "NO") for header in existing_headers]

        # 6. Push to Sheets (will now Update or Append correctly)
        self.sync_to_tab("Lifestyle_Log", final_row, existing_headers, is_list=False)
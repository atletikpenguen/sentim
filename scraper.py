#!/usr/bin/env python3
"""
Sentimentalgo Web Scraper
Scrapes data from sentimentalgo.com and updates Google Sheets
"""

import os
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LOGIN_URL = "https://app.sentimentalgo.com/signin"
TARGET_URL = "https://app.sentimentalgo.com/bist/lines"
EMAIL = os.getenv("SENTIMENT_EMAIL", "atletikpenguen@gmail.com")
PASSWORD = os.getenv("SENTIMENT_PASSWORD", "qwe1323")
SHEET_ID = os.getenv("SHEET_ID", "1daGabBAYapAd0sDqcvI6qn908Id2hz8Y")
SHEET_NAME = os.getenv("SHEET_NAME", "sent")
LAST_UPDATE_FILE = "last_update.txt"

# Google Sheets scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def get_last_update():
    """Read the last update value from file"""
    try:
        if os.path.exists(LAST_UPDATE_FILE):
            with open(LAST_UPDATE_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception as e:
        print(f"Error reading last update file: {e}")
    return None


def save_last_update(update_value):
    """Save the current update value to file"""
    try:
        with open(LAST_UPDATE_FILE, 'w', encoding='utf-8') as f:
            f.write(update_value)
        print(f"Saved last update: {update_value}")
    except Exception as e:
        print(f"Error saving last update: {e}")


def scrape_sentiment_data():
    """Scrape data from sentimentalgo.com"""
    print("Starting scraper...")

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        )
        page = context.new_page()

        try:
            # Step 1: Navigate to login page
            print("Navigating to login page...")
            page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=30000)
            time.sleep(2)
            page.screenshot(path="step1_login_page.png")
            print(f"Current URL: {page.url}")

            # Step 2: Fill login form
            print("Filling login form...")
            # Wait for email input and fill it
            page.wait_for_selector('input[type="email"], input[name="email"], input[id="email"]', timeout=10000)
            email_input = page.query_selector('input[type="email"], input[name="email"], input[id="email"]')
            if email_input:
                email_input.fill(EMAIL)
                print("Email filled")

            # Find password input and fill it
            password_input = page.query_selector('input[type="password"], input[name="password"], input[id="password"]')
            if password_input:
                password_input.fill(PASSWORD)
                print("Password filled")

            # Find and click submit button
            time.sleep(1)
            submit_button = page.query_selector('button[type="submit"], button:has-text("Giriş"), button:has-text("Login")')
            if submit_button:
                print("Clicking submit button...")
                submit_button.click()
            else:
                print("Submit button not found, pressing Enter...")
                page.keyboard.press("Enter")

            # Wait for navigation after login
            print("Waiting for login...")
            time.sleep(8)
            page.screenshot(path="step2_after_login.png")
            print(f"Current URL after login: {page.url}")

            # Check if login was successful
            if "signin" in page.url.lower():
                print("ERROR: Still on login page! Login may have failed.")
                page.screenshot(path="login_failed.png")
                browser.close()
                return None

            # Step 3: Navigate to target page
            print(f"Navigating to target page: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=30000)
            time.sleep(5)
            page.screenshot(path="step3_target_page.png")
            print(f"Current URL: {page.url}")

            # Step 4: Click on the tab
            print("Clicking on tab #rc-tabs-1-tab-999...")

            # Try multiple methods to find and click the tab
            tab_clicked = False

            # Method 1: XPath
            try:
                print("Method 1: Trying XPath selector...")
                tab_xpath = '//*[@id="rc-tabs-1-tab-999"]'
                tab_element = page.wait_for_selector(f'xpath={tab_xpath}', timeout=5000, state='attached')
                if tab_element:
                    # Scroll to element and wait for it to be visible
                    tab_element.scroll_into_view_if_needed()
                    time.sleep(1)
                    # Use JavaScript click to avoid interception issues
                    page.evaluate('(element) => element.click()', tab_element)
                    print("✓ Tab clicked successfully with XPath")
                    tab_clicked = True
                    time.sleep(3)
                    page.screenshot(path="step4_tab_clicked.png")
            except Exception as e:
                print(f"Method 1 failed: {e}")

            # Method 2: CSS ID selector with JavaScript
            if not tab_clicked:
                try:
                    print("Method 2: Trying CSS selector with JavaScript click...")
                    page.evaluate("document.getElementById('rc-tabs-1-tab-999')?.click()")
                    time.sleep(2)
                    # Check if it worked by looking for any table
                    tables = page.query_selector_all('table')
                    if tables:
                        print("✓ Tab clicked successfully with JavaScript")
                        tab_clicked = True
                        page.screenshot(path="step4_tab_clicked.png")
                except Exception as e:
                    print(f"Method 2 failed: {e}")

            # Method 3: Find tab by text containing "999" or "Tümü" (All)
            if not tab_clicked:
                try:
                    print("Method 3: Trying to find tab by text...")
                    all_tabs = page.query_selector_all('[role="tab"]')
                    print(f"Found {len(all_tabs)} tabs")
                    for i, tab in enumerate(all_tabs):
                        tab_text = tab.inner_text().strip()
                        print(f"  Tab {i+1}: '{tab_text}'")
                        # Look for "999" or "Tümü" or "Hepsi" or last numeric tab
                        if '999' in tab_text or 'Tümü' in tab_text or 'Hepsi' in tab_text or 'All' in tab_text.lower():
                            print(f"Found matching tab: '{tab_text}'")
                            tab.scroll_into_view_if_needed()
                            time.sleep(1)
                            page.evaluate('(element) => element.click()', tab)
                            print("✓ Tab clicked successfully by text match")
                            tab_clicked = True
                            time.sleep(3)
                            page.screenshot(path="step4_tab_clicked.png")
                            break
                except Exception as e:
                    print(f"Method 3 failed: {e}")

            # Method 4: Click the last tab as final fallback
            if not tab_clicked:
                try:
                    print("Method 4: Clicking last tab as fallback...")
                    all_tabs = page.query_selector_all('[role="tab"]')
                    if all_tabs:
                        last_tab = all_tabs[-1]
                        last_tab.scroll_into_view_if_needed()
                        time.sleep(1)
                        page.evaluate('(element) => element.click()', last_tab)
                        print("✓ Clicked last tab as fallback")
                        tab_clicked = True
                        time.sleep(3)
                        page.screenshot(path="step4_tab_fallback.png")
                except Exception as e:
                    print(f"Method 4 failed: {e}")

            if not tab_clicked:
                print("⚠️  WARNING: Could not click any tab, proceeding anyway...")
                page.screenshot(path="step4_no_tab_clicked.png")

            # Step 5: Get last update time
            print("Checking last update time...")
            update_selector = '#root > section > section > main > div.gx-main-content-wrapper > div.gx-main-content > div.ant-card.ant-card-bordered.gx-card-full > div > div.ant-row > div.ant-col.ant-col-xs-8.ant-col-sm-8.ant-col-md-8.ant-col-lg-8 > div'

            try:
                update_element = page.wait_for_selector(update_selector, timeout=10000)
                current_update = update_element.inner_text().strip()
                print(f"Current update: {current_update}")

                # Check if update has changed
                last_update = get_last_update()
                print(f"Last saved update: {last_update}")

                if last_update and last_update == current_update:
                    print("No changes detected. Skipping update.")
                    browser.close()
                    return None

                print("Change detected! Scraping table data...")

            except PlaywrightTimeout:
                print("Warning: Could not find update time element")
                current_update = f"Unknown - {datetime.now().strftime('%d.%m.%Y %H:%M')}"

            # Step 6: Scrape table data
            table_selector = '#root > section > section > main > div.gx-main-content-wrapper > div.gx-main-content > div.ant-card.ant-card-bordered.gx-card-full > div > div.step-lines-tables'

            print("Waiting for table data...")
            try:
                page.wait_for_selector(table_selector, timeout=15000)
                time.sleep(3)
                page.screenshot(path="step5_table_ready.png")
            except PlaywrightTimeout:
                print(f"Warning: Table selector '{table_selector}' not found, trying to find any table...")
                page.screenshot(path="step5_no_table.png")

            # Get all tables within the container
            tables = page.query_selector_all(f'{table_selector} table')

            # If no tables found with specific selector, try generic selector
            if not tables:
                print("Trying generic table selector...")
                tables = page.query_selector_all('table')

            if not tables:
                print("ERROR: No tables found on the page!")
                page.screenshot(path="error_no_tables.png")
                browser.close()
                return None

            print(f"Found {len(tables)} table(s)")

            # Extract data from tables
            all_data = []

            for table_idx, table in enumerate(tables):
                print(f"Processing table {table_idx + 1}...")

                # Get headers
                headers = []
                header_cells = table.query_selector_all('thead th, thead td')
                for cell in header_cells:
                    headers.append(cell.inner_text().strip())

                # Get rows
                rows = table.query_selector_all('tbody tr')

                for row in rows:
                    cells = row.query_selector_all('td')
                    row_data = [cell.inner_text().strip() for cell in cells]

                    if row_data:  # Only add non-empty rows
                        # Add timestamp and update info
                        row_with_meta = [datetime.now().strftime('%d.%m.%Y %H:%M'), current_update] + row_data
                        all_data.append(row_with_meta)

            print(f"Extracted {len(all_data)} rows of data")

            # Take a screenshot for debugging
            page.screenshot(path="screenshot.png")
            print("Screenshot saved as screenshot.png")

            # Close browser
            browser.close()

            # Save the current update value
            save_last_update(current_update)

            # Return data with headers
            return {
                'update_time': current_update,
                'data': all_data,
                'headers': ['Tarih', 'Son Güncelleme'] + headers if headers else ['Tarih', 'Son Güncelleme']
            }

        except Exception as e:
            print(f"Error during scraping: {e}")
            # Take screenshot on error
            try:
                page.screenshot(path="error_screenshot.png")
                print("Error screenshot saved")
            except:
                pass
            browser.close()
            raise


def update_google_sheet(data):
    """Update Google Sheets with scraped data"""
    print("Updating Google Sheet...")

    try:
        # Load credentials
        creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

        if not os.path.exists(creds_file):
            print(f"Error: Credentials file '{creds_file}' not found!")
            print("Please create a Google Service Account and download the credentials.")
            return False

        # Authenticate
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        client = gspread.authorize(creds)

        # Open spreadsheet
        print(f"Opening spreadsheet: {SHEET_ID}")
        spreadsheet = client.open_by_key(SHEET_ID)
        print(f"Spreadsheet opened: {spreadsheet.title}")

        # Try to get the worksheet, create if it doesn't exist
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
            print(f"Found worksheet: {SHEET_NAME}")
        except gspread.exceptions.WorksheetNotFound:
            print(f"Worksheet '{SHEET_NAME}' not found, creating it...")
            worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)

        # Get existing data to check if we need headers
        try:
            existing_data = worksheet.get_all_values()
            print(f"Existing data rows: {len(existing_data)}")
        except Exception as e:
            print(f"Warning: Could not read existing data: {e}")
            existing_data = []

        # Prepare rows to add
        rows_to_add = []

        # If sheet is empty, add headers
        if not existing_data:
            print("Sheet is empty, adding headers...")
            rows_to_add.append(data['headers'])

        # Add data rows
        rows_to_add.extend(data['data'])

        # Calculate the starting row
        start_row = len(existing_data) + 1

        print(f"Adding {len(rows_to_add)} rows starting from row {start_row}")

        # Use batch update for better performance and compatibility
        try:
            # Method 1: Try using values().append() API
            print("Method 1: Using values().append() API...")
            worksheet.append_rows(rows_to_add, value_input_option='RAW')
            print(f"✓ Successfully added {len(data['data'])} rows to Google Sheet")
            return True
        except Exception as e1:
            print(f"Method 1 failed: {e1}")

            try:
                # Method 2: Try using update() with range
                print("Method 2: Using update() with range...")
                end_row = start_row + len(rows_to_add) - 1
                end_col_letter = chr(65 + len(rows_to_add[0]) - 1)  # Convert to letter (A, B, C, etc.)
                range_name = f'A{start_row}:{end_col_letter}{end_row}'
                print(f"Updating range: {range_name}")
                worksheet.update(range_name, rows_to_add, value_input_option='RAW')
                print(f"✓ Successfully added {len(data['data'])} rows to Google Sheet")
                return True
            except Exception as e2:
                print(f"Method 2 failed: {e2}")

                try:
                    # Method 3: Add rows one by one (slowest but most compatible)
                    print("Method 3: Adding rows one by one...")
                    for i, row in enumerate(rows_to_add):
                        try:
                            row_num = start_row + i
                            range_name = f'A{row_num}'
                            worksheet.update(range_name, [row], value_input_option='RAW')
                            if i == 0 or (i + 1) % 5 == 0:
                                print(f"  Added {i + 1}/{len(rows_to_add)} rows...")
                        except Exception as e_row:
                            print(f"  Warning: Could not add row {i + 1}: {e_row}")
                            continue

                    print(f"✓ Added {len(rows_to_add)} rows to Google Sheet (with potential errors)")
                    return True
                except Exception as e3:
                    print(f"Method 3 failed: {e3}")
                    raise Exception(f"All methods failed. Last error: {e3}")

    except Exception as e:
        print(f"Error updating Google Sheet: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("=" * 50)
    print("Sentimentalgo Scraper")
    print("=" * 50)

    try:
        # Scrape data
        result = scrape_sentiment_data()

        if result is None:
            print("No new data to update.")
            return

        # Update Google Sheet
        success = update_google_sheet(result)

        if success:
            print("\n" + "=" * 50)
            print("SUCCESS: Data updated successfully!")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("FAILED: Could not update Google Sheet")
            print("=" * 50)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

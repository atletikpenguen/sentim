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
INDEX_URL = "https://app.sentimentalgo.com/index/home"
EMAIL = os.getenv("SENTIMENT_EMAIL", "atletikpenguen@gmail.com")
PASSWORD = os.getenv("SENTIMENT_PASSWORD", "qwe1323")
SHEET_ID = os.getenv("SHEET_ID", "1daGabBAYapAd0sDqcvI6qn908Id2hz8Y")
SHEET_NAME = os.getenv("SHEET_NAME", "sent")
INDEX_SHEET_NAME = os.getenv("INDEX_SHEET_NAME", "Sayfa2")
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

            # Step 4: Close any popups that might appear
            print("Checking for popups to close...")
            try:
                # Common popup close button selectors
                popup_close_selectors = [
                    'button.ant-modal-close',
                    '.ant-modal-close-x',
                    'button:has-text("Kapat")',
                    'button:has-text("Close")',
                    'button:has-text("×")',
                    '[aria-label="Close"]'
                ]
                for selector in popup_close_selectors:
                    try:
                        close_buttons = page.query_selector_all(selector)
                        for button in close_buttons:
                            if button.is_visible():
                                print(f"Closing popup with: {selector}")
                                button.click()
                                time.sleep(1)
                    except:
                        pass
            except Exception as e:
                print(f"Popup close attempt: {e}")

            # No need to click tabs - table is directly on the page!
            print("Table is directly on the page, no tab clicking needed")
            time.sleep(2)

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
            table_selector = '.step-lines-tables'

            print("Waiting for table data...")
            try:
                page.wait_for_selector(table_selector, timeout=15000)
                time.sleep(3)

                # Scroll page down to load more rows
                print("Scrolling page to load all data...")
                for scroll_i in range(10):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(0.5)

                # Try to find and click "Show More" or "Load More" buttons
                try:
                    show_more_selectors = [
                        'button:has-text("Daha Fazla")',
                        'button:has-text("Show More")',
                        'button:has-text("Load More")',
                        'button:has-text("Tümünü Göster")',
                        '.load-more',
                        '.show-more'
                    ]
                    for selector in show_more_selectors:
                        buttons = page.query_selector_all(selector)
                        for button in buttons:
                            try:
                                if button.is_visible():
                                    print(f"Found and clicking: {selector}")
                                    button.click()
                                    time.sleep(2)
                            except:
                                pass
                except:
                    pass

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

            # Extract data from tables WITH PAGINATION
            all_data = []

            # Get headers from first table
            headers = []
            if tables:
                header_cells = tables[0].query_selector_all('thead th, thead td')
                for cell in header_cells:
                    headers.append(cell.inner_text().strip())
                print(f"Headers: {headers}")

            # Process all pagination pages
            current_page = 1
            max_pages = 10  # Safety limit

            while current_page <= max_pages:
                print(f"\n--- Processing page {current_page} ---")

                # Wait for table to load
                time.sleep(2)

                # Re-query tables on current page
                tables = page.query_selector_all(f'{table_selector} table')
                if not tables:
                    tables = page.query_selector_all('table')

                if not tables:
                    print("No tables found on current page")
                    break

                # Extract data from current page
                table = tables[0]  # Use first table
                rows = table.query_selector_all('tbody tr')
                page_row_count = len(rows)
                print(f"Found {page_row_count} rows on page {current_page}")

                for row in rows:
                    cells = row.query_selector_all('td')
                    row_data = [cell.inner_text().strip() for cell in cells]

                    if row_data:  # Only add non-empty rows
                        # Add timestamp and update info
                        row_with_meta = [datetime.now().strftime('%d.%m.%Y %H:%M'), current_update] + row_data
                        all_data.append(row_with_meta)

                # Take screenshot of current page
                page.screenshot(path=f"page_{current_page}.png")

                # Try to find and click "next page" button
                print("Looking for next page button...")
                next_button_found = False

                try:
                    # Look for next button with various selectors
                    next_selectors = [
                        '.ant-pagination-next:not(.ant-pagination-disabled)',
                        'li.ant-pagination-next:not(.ant-pagination-disabled) button',
                        'button.ant-pagination-item-link[aria-label*="next"]',
                        '[title="Next Page"]'
                    ]

                    for selector in next_selectors:
                        next_button = page.query_selector(selector)
                        if next_button and next_button.is_visible():
                            # Check if button is not disabled
                            is_disabled = next_button.evaluate('el => el.disabled || el.parentElement.classList.contains("ant-pagination-disabled")')
                            if not is_disabled:
                                print(f"Clicking next button: {selector}")
                                next_button.click()
                                next_button_found = True
                                time.sleep(3)  # Wait for new page to load
                                break
                except Exception as e:
                    print(f"Error finding next button: {e}")

                if not next_button_found:
                    print(f"No more pages found. Finished at page {current_page}")
                    break

                current_page += 1

            print(f"Extracted {len(all_data)} rows of data")

            # Take a screenshot for debugging
            page.screenshot(path="screenshot.png")
            print("Screenshot saved as screenshot.png")

            # DON'T close browser yet - we need it for index data
            # browser.close()

            # Return browser, page, and data
            # NOTE: Do NOT save last_update here! Only save after successful Google Sheets write
            return (browser, page, {
                'update_time': current_update,
                'data': all_data,
                'headers': ['Tarih', 'Son Güncelleme'] + headers if headers else ['Tarih', 'Son Güncelleme']
            })

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


def scrape_index_data(page):
    """Scrape index data from pano tab - uses existing logged-in page"""
    print("\n" + "="*50)
    print("Starting Index Data Scraper...")
    print("="*50)

    try:
        # Navigate to index page
        print(f"Navigating to index page: {INDEX_URL}")
        page.goto(INDEX_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        page.screenshot(path="index_step1_home.png")

        # Close any popups
        print("Checking for popups...")
        try:
            popup_close_selectors = [
                'button.ant-modal-close',
                '.ant-modal-close-x',
                'button:has-text("Kapat")',
                'button:has-text("Close")'
            ]
            for selector in popup_close_selectors:
                try:
                    close_buttons = page.query_selector_all(selector)
                    for button in close_buttons:
                        if button.is_visible():
                            button.click()
                            time.sleep(1)
                except:
                    pass
        except:
            pass

        # Click on "Pano" tab
        print("Looking for 'Pano' tab...")
        pano_clicked = False

        # Try multiple selectors for Pano tab
        pano_selectors = [
            '[role="tab"]:has-text("Pano")',
            'button:has-text("Pano")',
            '.ant-tabs-tab:has-text("Pano")',
        ]

        for selector in pano_selectors:
            try:
                pano_tab = page.query_selector(selector)
                if pano_tab and pano_tab.is_visible():
                    print(f"Found Pano tab with: {selector}")
                    pano_tab.click()
                    pano_clicked = True
                    time.sleep(3)
                    break
            except Exception as e:
                print(f"Selector {selector} failed: {e}")

        if not pano_clicked:
            # Try finding by text in all tabs
            all_tabs = page.query_selector_all('[role="tab"]')
            for tab in all_tabs:
                tab_text = tab.inner_text().strip()
                if 'Pano' in tab_text or 'pano' in tab_text.lower():
                    print(f"Found Pano tab by text: {tab_text}")
                    tab.click()
                    pano_clicked = True
                    time.sleep(3)
                    break

        if not pano_clicked:
            print("ERROR: Could not find Pano tab!")
            return None

        page.screenshot(path="index_step2_pano_clicked.png")

        # Wait for table to load
        print("Waiting for table...")
        time.sleep(3)

        # Find table
        tables = page.query_selector_all('table')
        if not tables:
            print("ERROR: No tables found!")
            return None

        print(f"Found {len(tables)} table(s)")

        # Extract data
        table = tables[0]

        # Get headers
        headers = []
        header_cells = table.query_selector_all('thead th, thead td')
        for cell in header_cells:
            headers.append(cell.inner_text().strip())

        # Add "Son Çekilme Tarihi" to headers
        headers.append('Son Çekilme Tarihi')
        print(f"Headers: {headers}")

        # Get rows
        rows = table.query_selector_all('tbody tr')
        print(f"Found {len(rows)} rows")

        all_data = []
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M')

        for row in rows:
            cells = row.query_selector_all('td')
            row_data = [cell.inner_text().strip() for cell in cells]

            if row_data:
                # Add timestamp as last column
                row_data.append(current_time)
                all_data.append(row_data)

        print(f"Extracted {len(all_data)} rows of index data")
        page.screenshot(path="index_final.png")

        return {
            'data': all_data,
            'headers': headers
        }

    except Exception as e:
        print(f"Error scraping index data: {e}")
        import traceback
        traceback.print_exc()
        return None


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
        write_success = False

        # Always use update() with explicit range to avoid column offset issues
        try:
            # Method 1: Try using update() with range (most reliable)
            print("Method 1: Using update() with explicit range...")
            end_row = start_row + len(rows_to_add) - 1

            # Calculate column letter (handle columns beyond Z)
            num_cols = len(rows_to_add[0])
            if num_cols <= 26:
                end_col_letter = chr(64 + num_cols)  # A=65, so 64+1=A
            else:
                # For columns beyond Z (AA, AB, etc.)
                first_letter = chr(64 + (num_cols - 1) // 26)
                second_letter = chr(65 + (num_cols - 1) % 26)
                end_col_letter = first_letter + second_letter

            range_name = f'A{start_row}:{end_col_letter}{end_row}'
            print(f"Updating range: {range_name} ({len(rows_to_add)} rows, {num_cols} columns)")
            worksheet.update(range_name, rows_to_add, value_input_option='RAW')
            print(f"✓ Successfully added {len(data['data'])} rows to Google Sheet")
            write_success = True
        except Exception as e1:
            print(f"Method 1 failed: {e1}")

            try:
                # Method 2: Try using append_rows as fallback
                print("Method 2: Using values().append() API...")
                worksheet.append_rows(rows_to_add, value_input_option='RAW', table_range='A1')
                print(f"✓ Successfully added {len(data['data'])} rows to Google Sheet")
                write_success = True
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
                    write_success = True
                except Exception as e3:
                    print(f"Method 3 failed: {e3}")
                    raise Exception(f"All methods failed. Last error: {e3}")

        # Apply column formatting if write was successful
        if write_success:
            try:
                print("Applying column formatting...")
                # Column indices (0-based):
                # A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8, J=9, K=10, L=11, M=12
                # E, F, I, L, M = numbers (4, 5, 8, 11, 12)
                # G, K = percentages (6, 10)
                # H = date (7)

                format_requests = []

                # Number format for E, F, I, L, M columns (decimal with comma)
                number_columns = [4, 5, 8, 11, 12]  # E, F, I, L, M
                for col in number_columns:
                    format_requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": worksheet.id,
                                "startColumnIndex": col,
                                "endColumnIndex": col + 1,
                                "startRowIndex": 1  # Skip header
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {
                                        "type": "NUMBER",
                                        "pattern": "#,##0.00"
                                    }
                                }
                            },
                            "fields": "userEnteredFormat.numberFormat"
                        }
                    })

                # Percentage format for G, K columns
                percent_columns = [6, 10]  # G, K
                for col in percent_columns:
                    format_requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": worksheet.id,
                                "startColumnIndex": col,
                                "endColumnIndex": col + 1,
                                "startRowIndex": 1  # Skip header
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "numberFormat": {
                                        "type": "PERCENT",
                                        "pattern": "0.00%"
                                    }
                                }
                            },
                            "fields": "userEnteredFormat.numberFormat"
                        }
                    })

                # Date format for H column
                format_requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startColumnIndex": 7,  # H
                            "endColumnIndex": 8,
                            "startRowIndex": 1  # Skip header
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "DATE",
                                    "pattern": "dd.mm.yyyy"
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                })

                # Apply all formatting
                spreadsheet.batch_update({"requests": format_requests})
                print("✓ Column formatting applied successfully")

            except Exception as e_format:
                print(f"Warning: Could not apply formatting: {e_format}")
                # Don't fail the whole operation if formatting fails

        return write_success

    except Exception as e:
        print(f"Error updating Google Sheet: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_google_sheet_index(data):
    """Update Google Sheets Sayfa2 with index data - UPSERT based on first column"""
    print("\nUpdating Google Sheet (Index Data - Sayfa2)...")

    try:
        # Load credentials
        creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

        if not os.path.exists(creds_file):
            print(f"Error: Credentials file '{creds_file}' not found!")
            return False

        # Authenticate
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        client = gspread.authorize(creds)

        # Open spreadsheet
        print(f"Opening spreadsheet: {SHEET_ID}")
        spreadsheet = client.open_by_key(SHEET_ID)

        # Try to get Sayfa2, create if it doesn't exist
        try:
            worksheet = spreadsheet.worksheet(INDEX_SHEET_NAME)
            print(f"Found worksheet: {INDEX_SHEET_NAME}")
        except gspread.exceptions.WorksheetNotFound:
            print(f"Worksheet '{INDEX_SHEET_NAME}' not found, creating it...")
            worksheet = spreadsheet.add_worksheet(title=INDEX_SHEET_NAME, rows=100, cols=20)

        # Get existing data
        try:
            existing_data = worksheet.get_all_values()
            print(f"Existing data rows: {len(existing_data)}")
        except Exception as e:
            print(f"Warning: Could not read existing data: {e}")
            existing_data = []

        # If sheet is empty, add headers
        if not existing_data:
            print("Sheet is empty, adding headers...")
            worksheet.update('A1', [data['headers']], value_input_option='RAW')
            existing_data = [data['headers']]

        # Build a mapping of first column values to row numbers
        # existing_data[0] is headers, so data starts from row 2 (index 1)
        index_map = {}
        for i, row in enumerate(existing_data[1:], start=2):  # Start from row 2
            if row:  # Skip empty rows
                first_col_value = row[0].strip() if row[0] else ''
                if first_col_value:
                    index_map[first_col_value] = i

        print(f"Found {len(index_map)} existing index names")

        # Process each data row - UPSERT based on first column
        updates = []  # List of (range, values) tuples for batch update

        for row_data in data['data']:
            if not row_data:
                continue

            first_col_value = row_data[0].strip()

            if first_col_value in index_map:
                # UPDATE existing row
                row_num = index_map[first_col_value]
                print(f"Updating row {row_num}: {first_col_value}")

                # Calculate column range
                num_cols = len(row_data)
                if num_cols <= 26:
                    end_col_letter = chr(64 + num_cols)
                else:
                    first_letter = chr(64 + (num_cols - 1) // 26)
                    second_letter = chr(65 + (num_cols - 1) % 26)
                    end_col_letter = first_letter + second_letter

                range_name = f'A{row_num}:{end_col_letter}{row_num}'
                updates.append((range_name, [row_data]))

            else:
                # INSERT new row at the end
                next_row = len(existing_data) + 1 + len([u for u in updates if 'A' + str(len(existing_data) + 1) in u[0]])
                print(f"Inserting new row {next_row}: {first_col_value}")

                num_cols = len(row_data)
                if num_cols <= 26:
                    end_col_letter = chr(64 + num_cols)
                else:
                    first_letter = chr(64 + (num_cols - 1) // 26)
                    second_letter = chr(65 + (num_cols - 1) % 26)
                    end_col_letter = first_letter + second_letter

                range_name = f'A{next_row}:{end_col_letter}{next_row}'
                updates.append((range_name, [row_data]))
                index_map[first_col_value] = next_row

        # Perform batch update
        print(f"Performing {len(updates)} updates...")
        for range_name, values in updates:
            try:
                worksheet.update(range_name, values, value_input_option='RAW')
            except Exception as e:
                print(f"Warning: Could not update {range_name}: {e}")

        print(f"✓ Successfully updated {len(updates)} rows in Sayfa2")
        return True

    except Exception as e:
        print(f"Error updating index sheet: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("=" * 50)
    print("Sentimentalgo Scraper")
    print("=" * 50)

    try:
        # Use a single Playwright context for both scrapers
        with sync_playwright() as p:
            # Launch browser once for both scrapers
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            )
            page = context.new_page()

            try:
                # Login first
                print("Logging in...")
                page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=30000)
                time.sleep(2)
                page.screenshot(path="step1_login_page.png")

                # Fill login form
                page.wait_for_selector('input[type="email"], input[name="email"], input[id="email"]', timeout=10000)
                email_input = page.query_selector('input[type="email"], input[name="email"], input[id="email"]')
                if email_input:
                    email_input.fill(EMAIL)
                    print("Email filled")

                password_input = page.query_selector('input[type="password"], input[name="password"], input[id="password"]')
                if password_input:
                    password_input.fill(PASSWORD)
                    print("Password filled")

                time.sleep(1)
                submit_button = page.query_selector('button[type="submit"], button:has-text("Giriş"), button:has-text("Login")')
                if submit_button:
                    print("Clicking submit button...")
                    submit_button.click()
                else:
                    print("Submit button not found, pressing Enter...")
                    page.keyboard.press("Enter")

                # Wait for login
                print("Waiting for login...")
                time.sleep(8)
                page.screenshot(path="step2_after_login.png")
                print(f"Current URL after login: {page.url}")

                # Check if login was successful
                if "signin" in page.url.lower():
                    print("ERROR: Still on login page! Login may have failed.")
                    page.screenshot(path="login_failed.png")
                    browser.close()
                    return

                # Scrape stock data (pass the logged-in page)
                print("\n--- Scraping Stock Data ---")
                stock_data = scrape_sentiment_data_with_page(page)

                if stock_data:
                    # Update Google Sheet with stock data
                    print("\n--- Updating Stock Data (Sayfa1) ---")
                    success_stock = update_google_sheet(stock_data)

                    if success_stock:
                        save_last_update(stock_data['update_time'])
                        print("✓ Stock data updated successfully!")
                    else:
                        print("✗ Failed to update stock data")
                        print("⚠️  last_update.txt NOT updated - will retry next time")
                else:
                    print("✗ Failed to scrape stock data")
                    success_stock = False

                # Scrape index data (using the same page)
                print("\n--- Scraping Index Data ---")
                index_data = scrape_index_data(page)

                if index_data:
                    # Update Google Sheet with index data
                    print("\n--- Updating Index Data (Sayfa2) ---")
                    success_index = update_google_sheet_index(index_data)

                    if success_index:
                        print("✓ Index data updated successfully!")
                    else:
                        print("✗ Failed to update index data")
                else:
                    print("✗ Failed to scrape index data")
                    success_index = False

                # Close browser
                browser.close()
                print("\n✓ Browser closed")

                # Print final summary
                print("\n" + "=" * 50)
                if success_stock and success_index:
                    print("SUCCESS: All data updated successfully!")
                elif success_stock:
                    print("PARTIAL SUCCESS: Stock data updated, but index data failed")
                else:
                    print("FAILED: Could not update data")
                print("=" * 50)

            except Exception as e:
                print(f"Error during scraping: {e}")
                import traceback
                traceback.print_exc()
                try:
                    browser.close()
                except:
                    pass

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


def scrape_sentiment_data_with_page(page):
    """Scrape stock data using an already logged-in page"""
    try:
        # Navigate to target page
        print(f"Navigating to target page: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(5)
        page.screenshot(path="step3_target_page.png")
        print(f"Current URL: {page.url}")

        # Close any popups
        print("Checking for popups to close...")
        try:
            popup_close_selectors = [
                'button.ant-modal-close',
                '.ant-modal-close-x',
                'button:has-text("Kapat")',
                'button:has-text("Close")',
                'button:has-text("×")',
                '[aria-label="Close"]'
            ]
            for selector in popup_close_selectors:
                try:
                    close_buttons = page.query_selector_all(selector)
                    for button in close_buttons:
                        if button.is_visible():
                            print(f"Closing popup with: {selector}")
                            button.click()
                            time.sleep(1)
                except:
                    pass
        except Exception as e:
            print(f"Popup close attempt: {e}")

        print("Table is directly on the page, no tab clicking needed")
        time.sleep(2)

        # Get last update time
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
                return None

            print("Change detected! Scraping table data...")

        except PlaywrightTimeout:
            print("Warning: Could not find update time element")
            current_update = f"Unknown - {datetime.now().strftime('%d.%m.%Y %H:%M')}"

        # Scrape table data
        table_selector = '.step-lines-tables'

        print("Waiting for table data...")
        try:
            page.wait_for_selector(table_selector, timeout=15000)
            time.sleep(3)

            # Scroll page down to load more rows
            print("Scrolling page to load all data...")
            for scroll_i in range(10):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(0.5)

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
            return None

        print(f"Found {len(tables)} table(s)")

        # Extract data from tables WITH PAGINATION
        all_data = []

        # Get headers from first table
        headers = []
        if tables:
            header_cells = tables[0].query_selector_all('thead th, thead td')
            for cell in header_cells:
                headers.append(cell.inner_text().strip())
            print(f"Headers: {headers}")

        # Process all pagination pages
        current_page = 1
        max_pages = 10

        while current_page <= max_pages:
            print(f"\n--- Processing page {current_page} ---")

            time.sleep(2)

            # Re-query tables on current page
            tables = page.query_selector_all(f'{table_selector} table')
            if not tables:
                tables = page.query_selector_all('table')

            if not tables:
                print("No tables found on current page")
                break

            # Extract data from current page
            table = tables[0]
            rows = table.query_selector_all('tbody tr')
            page_row_count = len(rows)
            print(f"Found {page_row_count} rows on page {current_page}")

            for row in rows:
                cells = row.query_selector_all('td')
                row_data = [cell.inner_text().strip() for cell in cells]

                if row_data:
                    row_with_meta = [datetime.now().strftime('%d.%m.%Y %H:%M'), current_update] + row_data
                    all_data.append(row_with_meta)

            # Take screenshot of current page
            page.screenshot(path=f"page_{current_page}.png")

            # Try to find and click "next page" button
            print("Looking for next page button...")
            next_button_found = False

            try:
                next_selectors = [
                    '.ant-pagination-next:not(.ant-pagination-disabled)',
                    'li.ant-pagination-next:not(.ant-pagination-disabled) button',
                    'button.ant-pagination-item-link[aria-label*="next"]',
                    '[title="Next Page"]'
                ]

                for selector in next_selectors:
                    next_button = page.query_selector(selector)
                    if next_button and next_button.is_visible():
                        is_disabled = next_button.evaluate('el => el.disabled || el.parentElement.classList.contains("ant-pagination-disabled")')
                        if not is_disabled:
                            print(f"Clicking next button: {selector}")
                            next_button.click()
                            next_button_found = True
                            time.sleep(3)
                            break
            except Exception as e:
                print(f"Error finding next button: {e}")

            if not next_button_found:
                print(f"No more pages found. Finished at page {current_page}")
                break

            current_page += 1

        print(f"Extracted {len(all_data)} rows of data")
        page.screenshot(path="screenshot.png")
        print("Screenshot saved as screenshot.png")

        return {
            'update_time': current_update,
            'data': all_data,
            'headers': ['Tarih', 'Son Güncelleme'] + headers if headers else ['Tarih', 'Son Güncelleme']
        }

    except Exception as e:
        print(f"Error during scraping: {e}")
        page.screenshot(path="error_screenshot.png")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

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
            tab_selector = '#rc-tabs-1-tab-999'
            try:
                page.wait_for_selector(tab_selector, timeout=15000)
                page.click(tab_selector)
                print("Tab clicked successfully")
                time.sleep(3)
                page.screenshot(path="step4_tab_clicked.png")
            except PlaywrightTimeout:
                print(f"Warning: Tab selector '{tab_selector}' not found, trying alternative methods...")
                # Try to find any tab with text containing numbers
                all_tabs = page.query_selector_all('[role="tab"]')
                print(f"Found {len(all_tabs)} tabs")
                if all_tabs:
                    # Click the last tab (usually the one with all data)
                    all_tabs[-1].click()
                    print("Clicked last tab as fallback")
                    time.sleep(3)
                    page.screenshot(path="step4_tab_fallback.png")

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
        spreadsheet = client.open_by_key(SHEET_ID)

        # Try to get the worksheet, create if it doesn't exist
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            print(f"Worksheet '{SHEET_NAME}' not found, creating it...")
            worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)

        # Get existing data to append
        existing_data = worksheet.get_all_values()

        # If sheet is empty, add headers
        if not existing_data:
            worksheet.append_row(data['headers'])

        # Append new data
        for row in data['data']:
            worksheet.append_row(row)

        print(f"Successfully added {len(data['data'])} rows to Google Sheet")
        return True

    except Exception as e:
        print(f"Error updating Google Sheet: {e}")
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

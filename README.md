# Whop Trading Discord Community Scraper

## Overview

This program scrapes all Discord communities on [Whop.com](https://whop.com) that are tagged as `trading` and stores the results in a CSV file. It uses Selenium to automate browser actions, including login and multi-factor authentication (MFA).

## Features
- Scrapes all or a specified number of trading communities from Whop's leaderboard
- Handles login and MFA (manual code entry required)
- Saves and reuses session cookies for faster subsequent runs
- Supports .env file for automatic email entry (no prompt)
- Outputs a well-structured CSV with all relevant community data

## Account Creation (Recommended Flow)
To use this scraper, you need a Whop.com account. For the smoothest experience, follow these steps:

1. **Sign up on [Whop.com](https://whop.com) using OAuth (e.g., Discord, Google, etc.)**
2. **When signing up, use an OAuth provider (like Discord) that is linked to an email address you control.**
   - For example, if you sign up with Discord and your Discord account uses `test@gmail.com`, that is the email you will use for login and MFA.
3. **After signing up, verify your email with Whop if prompted.**
4. **When running the scraper, input the same email (e.g., `test@gmail.com`) when prompted, or set it in the `.env` file.**
5. **Check your email inbox for the MFA code and enter it into the script when asked.**

> **Note:** The email you use to log in to the script must match the email associated with your Whop.com account (via OAuth or direct signup).

## Requirements
- Python 3.8+
- Google Chrome browser
- ChromeDriver (automatically managed by the script)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Environment Variables

You can create a `.env` file (see `.env.example`) to store your Whop email address. If `USERNAME` is set in `.env`, the script will use it automatically and will not prompt you for your email.

Example `.env`:
```
USERNAME=your_email@example.com
```

## Usage

### Basic Usage (Scrape up to 300 pages)
```bash
python main.py
```

### Scrape a Specific Number of Pages
To scrape only the first N pages (e.g., 2 pages):
```bash
python main.py 2
```
This will scrape from page 1 to 2.

If you provide an invalid value, the script will default to 300 pages.

### Login & Account Setup
- On the first run, the script will prompt you for your email (unless set in `.env`) and require you to enter the MFA code sent to your email.
- After a successful login, session cookies are saved to `whop_cookies.pkl` for future runs.
- On subsequent runs, if the cookies are still valid, you will not be prompted for login again.
- If cookies expire, you will be prompted to log in again.

## Output
- The results are saved to `whop_trading_communities.csv` in the current directory.

## Notes
- The script uses a real browser and may take several minutes to complete, depending on the number of pages.
- Do not close the browser window during operation.
- If Whop.com changes their website layout, you may need to update the XPaths in the script.

## Example Scrape URL
```
https://whop.com/discover/leaderboards/c/trading/p/{page_num}/
```
For example:
```
https://whop.com/discover/leaderboards/c/trading/p/1
```

---

**For any issues or feature requests, please open an issue or pull request.**


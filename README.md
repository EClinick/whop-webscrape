### OVERVIEW

This program scrapes all the discord communities Whop offers that are tagged as `trading` and stores it in a CSV.

---

### Setup Instructions

1. **Ensure you have Python 3.11 installed.**
   - You can check with: `py -3.11 --version`

2. **Create and activate a virtual environment:**
   ```bash
   py -3.11 -m venv venv
   # On Windows (cmd):
   venv\Scripts\activate
   # On Git Bash or WSL:
   source venv/Scripts/activate
   ```

3. **Install requirements:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   This will install:
   - selenium
   - webdriver-manager
   - browser-use (for login automation)
   - langchain-openai
   - playwright
   - python-dotenv

4. **Set up environment variables:**
   - Copy the `.env.example` file to `.env` (or create a new one)
   - Add your Gemini API key (required for Browser-Use login automation)
   - Add your Whop credentials (optional, if not provided you'll need to log in manually)
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   WHOP_USERNAME=your_whop_email_here
   WHOP_PASSWORD=your_whop_password_here
   ```

5. **Run Playwright installation:**
   ```bash
   playwright install
   ```

6. **Run the script:**
   ```bash
   python main.py
   ```

---

### Login Process

The script uses Browser-Use for handling authentication:

1. First, it checks for saved cookies in the `data/whop_cookies.json` file
2. If cookies exist, it tries to log in using them
3. If no cookies exist or they're expired:
   - If credentials are in the `.env` file, it attempts automatic login
   - Otherwise, it opens a browser window for manual login
4. After successful login, it saves the cookies for future use

To run only the login process (without scraping):
```bash
python login_handler.py
```

---

### Scraping Process

The link to scrape is:

```
https://whop.com/discover/leaderboards/c/trading/p/{page_num}/
```

Example:

https://whop.com/discover/leaderboards/c/trading/p/1

---

### Output

The script creates a CSV file with the following information:
- Basic community details (name, description, pricing, etc.)
- Ratings and reviews
- Features
- Social media links
- Profile information

The CSV is organized with columns grouped by category.


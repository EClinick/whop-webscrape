"""
Whop Login Handler

This script handles the login process for Whop using Browser-Use,
saving cookies for reuse in subsequent automation runs.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from browser_use import ActionResult, Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, SecretStr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("whop_automation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
COOKIES_FILE = os.path.join(DATA_DIR, "whop_cookies.json")

# Initialize LLM for Browser-Use agent
def get_llm():
    """Initialize and return the LLM for browser automation."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error('GEMINI_API_KEY is not set. Please set it in a .env file.')
        raise ValueError('GEMINI_API_KEY is not set. Please set it in a .env file.')
    return ChatGoogleGenerativeAI(model='gemini-2.0-flash-lite', api_key=SecretStr(api_key))

# Models for validation
class LoginResult(BaseModel):
    """Model for login status report."""
    is_logged_in: bool
    message: str

# Create controller for validation
controller = Controller()

@controller.registry.action('Report Login Status', param_model=LoginResult)
async def report_login_status(params: LoginResult):
    """Action to report login status."""
    logger.debug(f"Reporting login status: {params}")
    return ActionResult(
        is_done=True, 
        extracted_content=params.model_dump_json()
    )

async def login_to_whop(browser_context: BrowserContext) -> bool:
    """
    Log in to Whop using browser-use with cookies or automated login.
    
    Args:
        browser_context: The browser context to use
        
    Returns:
        True if login was successful, False otherwise
    """
    logger.info("Attempting to log in to Whop")
    
    # Get Whop credentials from environment variables
    whop_username = os.getenv('WHOP_USERNAME') or os.getenv('WHOP_EMAIL')
    whop_password = os.getenv('WHOP_PASSWORD')
    
    # Define a cookie saving function to avoid code duplication
    async def save_cookies():
        try:
            # Get cookies using the browser context directly
            cookies = await browser_context.page.cookies()
            with open(COOKIES_FILE, "w") as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Cookies saved to {COOKIES_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    # Check if cookies exist
    llm = get_llm()
    if os.path.exists(COOKIES_FILE):
        logger.info("Cookies file found, attempting to use stored cookies")
        
        # First attempt with cookies
        agent = Agent(
            browser_context=browser_context,
            task="Go to Whop.com and verify if we're logged in. Look for elements that indicate we're logged in like a profile icon, account menu, or personalized content. If there's any prompt or popup, dismiss it. When done, use the 'Report Login Status' action to report whether we're logged in or not with details about what you found.",
            llm=llm,
            controller=controller,
            validate_output=True,
            max_actions_per_step=4,
        )
        # Run the agent
        result = await agent.run(max_steps=10)
        
        # Check the result from the last action
        if result and result.is_done() and result.final_result():
            try:
                last_result = json.loads(result.final_result())
                if last_result.get("is_logged_in", False):
                    logger.info("Successfully logged in with cookies")
                    return True
                else:
                    logger.warning(f"Cookie login failed: {last_result.get('message', 'Unknown error')}")
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.error(f"Error parsing login result: {e}")
    
    # If we're here, either cookies didn't exist or cookie login failed
    logger.info("Attempting automated login with credentials")
    
    # Check if credentials are available
    if not whop_username or not whop_password:
        logger.warning("Whop credentials not found in environment variables")
        logger.info("Please set WHOP_USERNAME/WHOP_EMAIL and WHOP_PASSWORD environment variables or log in manually")
        
        # Create an agent for manual login
        agent = Agent(
            browser_context=browser_context,
            task="Go to Whop.com login page. Wait for the user to manually log in. Do not try to enter any credentials yourself, just wait for the user to log in manually. Once you detect that the user is logged in, use the 'Report Login Status' action to confirm successful login.",
            llm=llm,
            controller=controller,
            validate_output=True,
            max_actions_per_step=3,
        )
        
        # Run the agent to open the login page
        await agent.run(max_steps=5)
        
        logger.info("Please log in manually in the browser window")
        
        # Check periodically if user has logged in
        for i in range(60):  # Wait up to 5 minutes
            agent = Agent(
                browser_context=browser_context,
                task="Check if we're currently logged in to Whop. Look for elements that indicate a logged-in state like profile icon, account menu, or personalized content. Use the 'Report Login Status' action to report whether we're logged in or not.",
                llm=llm,
                controller=controller,
                validate_output=True,
                max_actions_per_step=3,
            )
            result = await agent.run(max_steps=5)
            
            # Check if login was successful
            if result and result.is_done() and result.final_result():
                try:
                    last_result = json.loads(result.final_result())
                    if last_result.get("is_logged_in", False):
                        logger.info("Manual login detected")
                        # Save cookies for future use
                        await save_cookies()
                        return True
                except (json.JSONDecodeError, AttributeError, TypeError) as e:
                    logger.error(f"Error parsing login result: {e}")
            await asyncio.sleep(5)
            if i % 12 == 0:  # Every minute
                logger.info("Still waiting for manual login...")
    else:
        # Create an agent for automated login
        agent = Agent(
            browser_context=browser_context,
            task=f"""Go to Whop.com login page. Look for the login form and use the following credentials:
            Email: {whop_username}
            Password: {whop_password}
            
            Enter the email, then the password, and click the login button.
            If there are any popups or prompts, dismiss them appropriately.
            After attempting login, verify if we're successfully logged in and use the 'Report Login Status' action to report whether we're logged in or not with details about what you found.
            
            If it asks for a verification code or additional security step, please wait for the user to complete it manually, then check login status again. If the there is popups with seemingly user related content, dismiss them.""",
            llm=llm,
            controller=controller,
            validate_output=True,
            max_actions_per_step=5,
        )
        
        # Run the agent to perform the login
        result = await agent.run(max_steps=7)
        
        # Check if login was successful
        if result and result.is_done() and result.final_result():
            try:
                last_result = json.loads(result.final_result())
                login_successful = last_result.get("is_logged_in", False)
                if login_successful:
                    logger.info("Automated login successful")
                    # Save cookies for future use
                    await save_cookies()
                    return True
                else:
                    logger.warning(f"Automated login failed: {last_result.get('message', 'Unknown error')}")
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.error(f"Error parsing login result: {e}")

    logger.error("Login timeout or failed")
    return False

async def get_cookies_for_selenium():
    """
    Get cookies for use with Selenium from the saved cookie file.
    
    Returns:
        List of cookie dictionaries if available, None otherwise
    """
    if not os.path.exists(COOKIES_FILE):
        logger.warning("No saved cookies found")
        return None
    
    try:
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
        return cookies
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return None

async def main():
    """Main function to run login process and save cookies."""
    # Create browser instance
    browser = Browser(config=BrowserConfig())
    
    try:
        # Create browser context
        context = BrowserContext(
            browser=browser, 
            config=BrowserContextConfig(cookies_file=COOKIES_FILE if os.path.exists(COOKIES_FILE) else None)
        )
        
        # Login to Whop
        success = await login_to_whop(context)
        if success:
            logger.info("Login successful, cookies saved for automated scraping")
        else:
            logger.error("Login failed")
        
        # Keep browser open briefly for verification
        await asyncio.sleep(2)
        
    except Exception as e:
        logger.error(f"An error occurred during login: {e}", exc_info=True)
    finally:
        # Close the browser
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 
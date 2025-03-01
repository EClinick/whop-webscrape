import time
import csv
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

class WhopTradingScraper:
    def __init__(self, headless=False):
        # Setup Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        # Initialize the browser
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Data storage
        self.communities = []
    
    def navigate_to_leaderboard_page(self, page_num=1):
        """Navigate to a specific page of the Whop trading leaderboard"""
        url = f"https://whop.com/discover/leaderboards/c/trading/p/{page_num}/"
        print(f"Navigating to leaderboard page {page_num}: {url}")
        self.driver.get(url)
        time.sleep(3)  # Let the page load
        
        # Check if page loaded successfully by looking for content
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main-content-with-header"]'))
            )
            return True
        except TimeoutException:
            print(f"Page {page_num} failed to load")
            return False
    
    def get_community_links_from_current_page(self):
        """Get community links and info from the current leaderboard page"""
        print("Getting community links from current page...")
        try:
            # Wait for the main container to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main-content-with-header"]'))
            )
            
            # Find all community cards
            community_cards = self.driver.find_elements(
                By.XPATH, '//*[@id="main-content-with-header"]/div[3]/ul/div'
            )
            
            community_links = []
            for card in community_cards:
                try:
                    # Get the link element which contains most of the info
                    link_element = card.find_element(By.TAG_NAME, 'a')
                    href = link_element.get_attribute('href')
                    
                    if href and '/discover/' in href:
                        # Extract data from the card before clicking
                        card_data = {
                            'url': href,
                            'name': self._safe_get_text_from_element(link_element, './/span[contains(@class, "fui-Text")]/span'),
                            'description': self._safe_get_text_from_element(link_element, './/span[contains(@class, "line-clamp-2")]'),
                            'price_badge': self._safe_get_text_from_element(link_element, './/span[contains(@class, "fui-Badge")]'),
                            'minutes_spent': self._safe_get_text_from_element(card, './/span[contains(text(), "minutes")]'),
                            'rating': self._get_rating_info(card),
                            'joined_count': self._safe_get_text_from_element(card, './/span[contains(text(), "joined")]'),
                        }
                        
                        print(f"Found community: {card_data['name']} at {href}")
                        community_links.append(card_data)
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    print(f"Error processing card: {e}")
                    continue
            
            print(f"Found {len(community_links)} community links on this page")
            return community_links
            
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error finding community links: {e}")
            return []
    
    def get_max_page_number(self):
        """Get the maximum page number from the pagination controls"""
        try:
            # Look for pagination elements
            pagination_elements = self.driver.find_elements(By.CSS_SELECTOR, 'ul[role="navigation"] button')
            max_page = 1
            
            for element in pagination_elements:
                text = element.text.strip()
                if text and text.isdigit():
                    page_num = int(text)
                    if page_num > max_page:
                        max_page = page_num
            
            print(f"Maximum page number detected: {max_page}")
            return max_page
        except NoSuchElementException:
            print("Pagination not found, assuming single page")
            return 1
    
    def scrape_community_info(self, community_data):
        """Scrape detailed information from a single community page"""
        print(f"Scraping: {community_data['url']}")
        self.driver.get(community_data['url'])
        time.sleep(random.uniform(2, 4))  # Random delay to avoid rate limiting
        
        try:
            # Wait for the page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1')))
            
            # Add additional information from the detailed page
            detailed_data = {
                **community_data,  # Include all data from the card
                'whop_ranking': self._safe_get_text(
                    '//span[contains(text(), "Whop Ranking")]'
                ),
                'founded_date': self._safe_get_text(
                    '//span[contains(text(), "Founded")]'
                ),
                'full_description': self._safe_get_text(
                    'div[role="paragraph"]'
                ),
                'features': self._get_features(),
                'social_links': self._get_social_links()
            }

            # Find and click View Profile button
            try:
                print("\nLooking for View Profile button...")
                view_profile_btn = self.wait.until(
                    EC.presence_of_element_located((
                        By.XPATH, "//button[contains(text(), 'View Profile')]"
                    ))
                )
                print("✓ Found View Profile button")
                
                # Scroll the button into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", view_profile_btn)
                time.sleep(1)  # Wait after scrolling
                
                # Click the button
                print("Clicking View Profile button...")
                view_profile_btn.click()
                time.sleep(2)  # Wait for modal to load
                
                # Get profile social links
                profile_links = self._get_profile_social_links()
                if profile_links:
                    detailed_data['profile_social_links'] = profile_links
                
                # Close the modal by pressing escape
                webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)  # Wait for modal to close
                
            except Exception as e:
                print(f"❌ Error with View Profile button: {e}")
            
            print(f"Successfully scraped detailed data for: {detailed_data['name']}")
            return detailed_data
            
        except TimeoutException:
            print(f"Timeout while scraping: {community_data['url']}")
            return community_data  # Return the basic data we already have
        except Exception as e:
            print(f"Error scraping {community_data['url']}: {e}")
            return community_data
    
    def _safe_get_text(self, selector):
        """Safely get text from an element, return empty string if not found"""
        try:
            if selector.startswith('//'):
                element = self.driver.find_element(By.XPATH, selector)
            else:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.text
        except NoSuchElementException:
            return ""
    
    def _safe_get_text_from_element(self, element, xpath):
        """Safely get text from an element using xpath"""
        try:
            return element.find_element(By.XPATH, xpath).text.strip()
        except NoSuchElementException:
            return ""
    
    def _get_rating_info(self, card):
        """Extract rating information from a card"""
        try:
            rating_element = card.find_element(By.XPATH, './/button[contains(@class, "fui-Button")]')
            rating_text = rating_element.text
            # Parse rating count and days
            parts = rating_text.split()
            return {
                'stars': len(rating_element.find_elements(By.XPATH, './/svg[contains(@fill, "currentColor")]')),
                'count': parts[0].strip('()'),
                'days_ago': parts[-1].strip()
            }
        except NoSuchElementException:
            return {}
    
    def _get_features(self):
        """Get feature list from community page"""
        features = []
        try:
            feature_elements = self.driver.find_elements(
                By.XPATH, '//div[contains(@class, "features")]//li'
            )
            for element in feature_elements:
                features.append(element.text.strip())
        except NoSuchElementException:
            pass
        return features
    
    def _get_social_links(self):
        """Get social media links from community page"""
        social_links = {}
        try:
            link_elements = self.driver.find_elements(
                By.XPATH, '//a[contains(@href, "discord.com") or contains(@href, "twitter.com")]'
            )
            for element in link_elements:
                href = element.get_attribute('href')
                if 'discord.com' in href:
                    social_links['discord'] = href
                elif 'twitter.com' in href:
                    social_links['twitter'] = href
        except NoSuchElementException:
            pass
        return social_links
    
    def get_profile_links(self):
        """Find and click View Profile buttons to get social links"""
        try:
            # Find all View Profile buttons
            profile_buttons = self.driver.find_elements(
                By.XPATH, "//button[contains(text(), 'View Profile')]"
            )
            
            print(f"Found {len(profile_buttons)} View Profile buttons")
            social_data = {}
            
            for i, button in enumerate(profile_buttons, 1):
                try:
                    print(f"\nProcessing profile button {i}/{len(profile_buttons)}")
                    
                    # Get the parent card to extract community name
                    card = button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'rounded-xl')]")
                    community_name = card.find_element(By.XPATH, ".//span[contains(@class, 'fui-Text')]/span").text
                    print(f"Processing community: {community_name}")
                    
                    # Scroll the button into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)  # Increased delay after scrolling
                    
                    # Click the View Profile button
                    print("Clicking View Profile button...")
                    button.click()
                    time.sleep(2)  # Wait for profile modal to load
                    
                    # Get all social links from the profile
                    print("Extracting social links...")
                    social_links = self._get_profile_social_links()
                    
                    if social_links:
                        social_data[community_name] = social_links
                        print(f"Successfully found social links for {community_name}")
                    else:
                        print(f"No social links found for {community_name}")
                    
                    # Close the profile modal by clicking escape
                    print("Closing profile modal...")
                    webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(1.5)  # Increased wait for modal to close
                    
                except Exception as e:
                    print(f"Error processing profile button: {e}")
                    # Try to close modal if it's still open
                    try:
                        webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    except:
                        pass
                    continue
            
            print(f"\nCompleted processing all profiles. Found data for {len(social_data)} communities")
            return social_data
                
        except Exception as e:
            print(f"Error finding profile buttons: {e}")
            return {}
    
    def _get_profile_social_links(self):
        """Extract social media links from an open profile modal"""
        social_links = {}
        try:
            print("\n=== Starting Profile Link Extraction ===")
            
            # First try to find the main container with the specific class
            print("Looking for main container...")
            main_container = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 'div[class*="relative mt-[22px]"]'
                ))
            )
            print("✓ Found main container")
            
            # Get username info
            try:
                print("Looking for username info...")
                username_spans = main_container.find_elements(
                    By.CSS_SELECTOR, 'span[class*="fui-Text"]'
                )
                for span in username_spans:
                    text = span.text
                    if '•' in text:
                        username, join_date = text.split('•')
                        social_links['username'] = username.strip()
                        social_links['join_date'] = join_date.strip()
                        print(f"✓ Found username: {username.strip()} and join date: {join_date.strip()}")
                        break
                else:
                    print("❌ No username info found in spans")
            except Exception as e:
                print(f"❌ Error getting username info: {e}")

            # Find the social links ul using the exact class
            print("\nLooking for social links container...")
            try:
                # Try both exact and partial class match
                try:
                    links_ul = main_container.find_element(
                        By.CSS_SELECTOR, 'ul[class="mx-auto mt-4 flex w-auto items-center gap-3"]'
                    )
                except:
                    links_ul = main_container.find_element(
                        By.CSS_SELECTOR, 'ul[class*="mx-auto mt-4"]'
                    )
                print("✓ Found social links container")
                
                # Get all li elements within the ul
                link_items = links_ul.find_elements(By.TAG_NAME, 'li')
                print(f"Found {len(link_items)} link items")
                
                if not link_items:
                    print("❌ No link items found in the container")
                
                for li in link_items:
                    try:
                        # Find the anchor tag within the li
                        link = li.find_element(By.TAG_NAME, 'a')
                        href = link.get_attribute('href')
                        aria_label = link.get_attribute('aria-label')
                        
                        print(f"\nProcessing link:")
                        print(f"- href: {href}")
                        print(f"- aria-label: {aria_label}")
                        
                        if href:
                            # Determine the platform from href and aria-label
                            platform = None
                            
                            # Check common social media platforms in the URL
                            if 'twitter.com' in href or 'x.com' in href:
                                platform = 'twitter'
                            elif 'instagram.com' in href:
                                platform = 'instagram'
                            elif 'youtube.com' in href or 'youtu.be' in href:
                                platform = 'youtube'
                            elif 'tiktok.com' in href:
                                platform = 'tiktok'
                            elif 'facebook.com' in href or 'fb.com' in href:
                                platform = 'facebook'
                            elif 'discord' in href:
                                platform = 'discord'
                            else:
                                # Try to get platform from aria-label
                                if aria_label:
                                    label = aria_label.lower()
                                    if any(x in label for x in ['twitter', 'x.com']):
                                        platform = 'twitter'
                                    elif 'instagram' in label:
                                        platform = 'instagram'
                                    elif 'youtube' in label:
                                        platform = 'youtube'
                                    elif 'tiktok' in label:
                                        platform = 'tiktok'
                                    elif 'facebook' in label:
                                        platform = 'facebook'
                                    elif 'discord' in label:
                                        platform = 'discord'
                                    else:
                                        platform = 'website'
                                else:
                                    platform = 'website'
                            
                            if platform:
                                social_links[platform] = href
                                print(f"✓ Added {platform} link: {href}")
                            else:
                                print(f"❌ Could not determine platform for: {href}")
                        else:
                            print("❌ No href found for this link")
                                
                    except Exception as e:
                        print(f"❌ Error processing link item: {e}")
                        
            except Exception as e:
                print(f"❌ Error finding social links container: {e}")

            # Get bio text
            try:
                print("\nLooking for bio...")
                bio_element = main_container.find_element(
                    By.CSS_SELECTOR, 'p[class*="fui-Text max-w-[478px]"]'
                )
                if bio_element:
                    social_links['bio'] = bio_element.text
                    print(f"✓ Found bio: {bio_element.text[:100]}...")  # Show first 100 chars
                else:
                    print("❌ No bio element found")
            except Exception as e:
                print(f"❌ Error getting bio: {e}")

            print("\n=== Link Extraction Summary ===")
            if social_links:
                print(f"Total links found: {len(social_links)}")
                for key, value in social_links.items():
                    print(f"- {key}: {value}")
            else:
                print("❌ No social links were extracted")
            
        except Exception as e:
            print(f"❌ Major error in profile extraction: {e}")
        
        return social_links
    
    def scrape_all_communities(self, max_pages=None):
        """
        Scrape communities from the leaderboard
        Args:
            max_pages (int, optional): Maximum number of pages to scrape. If None, scrapes all pages.
        """
        page_num = 1
        all_community_data = []
        all_social_data = {}
        
        while True:
            print(f"\nProcessing page {page_num}")
            
            # Check if we've reached the max pages
            if max_pages and page_num > max_pages:
                print(f"Reached maximum pages limit of {max_pages}")
                break
                
            # Try to navigate to the page
            if not self.navigate_to_leaderboard_page(page_num):
                print(f"No more pages found after page {page_num - 1}")
                break
            
            # Get community links from current page
            page_links = self.get_community_links_from_current_page()
            
            if not page_links:
                print(f"No communities found on page {page_num}, stopping pagination")
                break
            
            # Get social links from profile sections
            page_social_data = self.get_profile_links()
            all_social_data.update(page_social_data)
            
            # Scrape each community page
            for link in page_links:
                community_data = self.scrape_community_info(link)
                if community_data:
                    # Add social data if available
                    if community_data['name'] in all_social_data:
                        community_data['profile_social_links'] = all_social_data[community_data['name']]
                    self.communities.append(community_data)
                    print(f"Successfully scraped: {community_data['name']}")
                
                # Add random delay between requests
                time.sleep(random.uniform(1, 3))
            
            page_num += 1
            # Add delay between pages
            time.sleep(random.uniform(2, 4))
        
        print(f"Completed scraping {len(self.communities)} communities across {page_num - 1} pages")
    
    def save_to_csv(self, filename="whop_trading_communities.csv"):
        """Save the scraped data to a CSV file with organized columns"""
        if not self.communities:
            print("No data to save.")
            return
        
        # Define column groups and their order
        column_groups = {
            'Basic Info': [
                'name',
                'url',
                'description',
                'full_description',
                'price_badge',
                'joined_count',
                'minutes_spent',
                'founded_date',
                'whop_ranking'
            ],
            'Rating': [
                'rating_stars',
                'rating_count',
                'rating_days_ago'
            ],
            'Features': [
                'features'
            ],
            'Profile Info': [
                'profile_social_links_username',
                'profile_social_links_join_date',
                'profile_social_links_bio'
            ],
            'Social Links': [
                'profile_social_links_twitter',
                'profile_social_links_x',
                'profile_social_links_instagram',
                'profile_social_links_youtube',
                'profile_social_links_tiktok',
                'profile_social_links_facebook',
                'profile_social_links_discord',
                'profile_social_links_website'
            ]
        }
        
        # Flatten and organize the data
        flattened_data = []
        for community in self.communities:
            flat_community = {}
            
            # Process basic fields
            for key, value in community.items():
                if key != 'profile_social_links' and not isinstance(value, dict):
                    flat_community[key] = value
            
            # Process profile social links
            if 'profile_social_links' in community:
                social_links = community['profile_social_links']
                for key, value in social_links.items():
                    # Map social media platforms to standardized names
                    if key in ['twitter', 'x']:
                        flat_community['profile_social_links_twitter'] = value
                    elif key == 'instagram':
                        flat_community['profile_social_links_instagram'] = value
                    elif key in ['youtube', 'yt']:
                        flat_community['profile_social_links_youtube'] = value
                    elif key == 'tiktok':
                        flat_community['profile_social_links_tiktok'] = value
                    elif key == 'facebook':
                        flat_community['profile_social_links_facebook'] = value
                    elif key == 'discord':
                        flat_community['profile_social_links_discord'] = value
                    elif key in ['website', 'url']:
                        flat_community['profile_social_links_website'] = value
                    elif key in ['username', 'join_date', 'bio']:
                        flat_community[f'profile_social_links_{key}'] = value
            
            flattened_data.append(flat_community)
        
        # Get all unique columns while maintaining order from column_groups
        fieldnames = []
        for group in column_groups.values():
            fieldnames.extend(group)
        
        # Add any remaining columns that weren't in our predefined groups
        all_keys = set()
        for community in flattened_data:
            all_keys.update(community.keys())
        remaining_fields = sorted(list(all_keys - set(fieldnames)))
        fieldnames.extend(remaining_fields)
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write data with organized columns
            for community in flattened_data:
                # Ensure all fields exist (with empty strings for missing data)
                row = {field: community.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        print(f"Data saved to {filename} with organized columns")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

def main():
    # Initialize the scraper
    scraper = WhopTradingScraper(headless=False)  # Set to True for headless mode
    
    try:
        # Run the scraping process
        scraper.scrape_all_communities(max_pages=200)
        
        # Save the data
        scraper.save_to_csv()
        
        print("Scraping completed successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Always close the browser
        scraper.close()

if __name__ == "__main__":
    main()
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import queue

class AsyncWebDriver:
    def __init__(self, driver):
        self.driver = driver

    async def __aenter__(self):
        return self.driver

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            return self.driver.quit()

class TweetCapture:
    
    max_drivers = 5
    driver_pool = queue.Queue()
    
    @classmethod
    async def get_driver(cls):
        if cls.driver_pool.empty():
            chrome_options = cls.setup_chrome_options()
            chrome_service = webdriver.chrome.service.Service(ChromeDriverManager().install())
            try:
                driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
                driver.set_window_size(1920, 1080)
            except Exception as e:
                print(f"Failed to initialize Chrome driver: {str(e)}")
                return None
        else:
            driver = cls.driver_pool.get()

        if driver is not None:
            return AsyncWebDriver(driver)
        else:
            return None
    
    @classmethod
    async def release_driver(cls, driver):
        cls.driver_pool.put(driver)
        if cls.driver_pool.qsize() > cls.max_drivers:
            driver = cls.driver_pool.get()
            driver.quit()
    
    @staticmethod
    def setup_chrome_options():
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        return chrome_options
    
    @staticmethod
    def set_night_mode(driver, tweet_url, night_mode=None):
        """
        Sets the night mode and adds cookies to the Selenium WebDriver instance.
        
        Args:
            driver (webdriver.Chrome): The Selenium WebDriver instance.
            night_mode (bool, optional): The night mode setting. If not provided, it will use 0.
            cookies (list, optional): A list of cookies to be added to the WebDriver instance.
        """
        driver.get(tweet_url)
        # Set the night mode cookie
        driver.add_cookie(
            {"name": "night_mode", "value": str(night_mode if night_mode is not None else 0)}
        )
                
    @staticmethod
    def dismiss_cookie_accept(driver):
        try:
            cookie_accept_button = driver.find_element(By.CSS_SELECTOR, "div[role='button'][class*='r-sdzlij'][class*='r-1phboty']")
            driver.execute_script("arguments[0].click();", cookie_accept_button)
        except:
            pass
    
    @staticmethod
    def find_main_tweet_element(driver):
        tweet_elements = driver.find_elements(By.XPATH, "(//ancestor::article)/..")
        for element in tweet_elements:
            if len(element.find_elements(By.XPATH, ".//article[contains(@data-testid, 'tweet')]")) > 0:
                source = element.get_attribute("innerHTML")
                if source.find("M19.498 3h-15c-1.381 0-2.5 1.12-2.5 2.5v13c0 1.38") == -1 and source.find('css-1dbjc4n r-1s2bzr4" id="id__jrl5cg7nxl"') == -1:
                    main_tweet_details = element.find_elements(By.XPATH, ".//div[contains(@class, 'r-1471scf')]")
                    if len(main_tweet_details) == 1:
                        return element
        return None
    
    @staticmethod
    async def screenshot(tweet_url, screenshot_path, night_mode=0):
        async with await TweetCapture.get_driver() as driver:
            try:
                # Set the night mode and add cookies
                TweetCapture.set_night_mode(driver, tweet_url, night_mode)
                
                driver.get(tweet_url)
                
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "(//ancestor::article)/..")))
                main_tweet_element = TweetCapture.find_main_tweet_element(driver)

                if main_tweet_element is None:
                    raise Exception("Unable to locate the main tweet element.")

                # Scroll to the tweet element
                driver.execute_script("arguments[0].scrollIntoView(true);", main_tweet_element)

                # Get the dimensions of the tweet element
                tweet_rect = main_tweet_element.rect
                width = tweet_rect['width']
                height = tweet_rect['height']

                # Set the window size to match the tweet dimensions
                driver.set_window_size(width, height + 512)

                # Take the screenshot
                main_tweet_element.screenshot(screenshot_path)
            except Exception as e:
                raise(f"Internal Error: {str(e)}")
                
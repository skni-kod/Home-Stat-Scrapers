import csv
import datetime
import os
import time
from loguru import logger

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up logging using Loguru
log_folder = "logs"
os.makedirs(log_folder, exist_ok=True)
log_filename = os.path.join(log_folder, f"scraping_log_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
logger.add(log_filename, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}")

# Firefox and Geckodriver configuration
logger.info("Starting Firefox WebDriver configuration.")
service = Service("/usr/local/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)
logger.info("Firefox WebDriver started in headless mode.")

# Base URL and subsites to scrape
base_url = "https://zakupy.biedronka.pl"
subsites = ["warzywa", "owoce", "piekarnia", "nabial", "mieso",
            "dania-gotowe","napoje","mrozone","artykuly-spozywcze",
            "drogeria","dla-domu","dla-dzieci","dla-zwierzat"]

def has_next_page():
    try:
        driver.find_element(By.CSS_SELECTOR, "a.bucket-pagination__icon.bucket-pagination__icon--next")
        logger.debug("Next page button found.")
        return True
    except NoSuchElementException:
        logger.debug("No next page button found.")
        return False


def scrape_page(page_url, first_page=False, category="", data_list=None):
    if data_list is None:
        data_list = []
    logger.info(f"Scraping page: {page_url} for category: {category}")
    driver.get(page_url)

    if first_page:
        logger.info("Waiting extra time for the first page to fully load...")
        time.sleep(5)  # Extra wait for the first page

    # Scroll down to load dynamic content
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-grid__item"))
        )
        logger.debug("Product elements loaded successfully.")
    except TimeoutException:
        logger.error(f"Timeout waiting for page to load: {page_url}")
        return False

    products = driver.find_elements(By.CLASS_NAME, "product-grid__item")
    if not products:
        logger.warning(f"No products found on page: {page_url}.")
        return False

    logger.info(f"Found {len(products)} products on page: {page_url}")

    for product in products:
        try:
            # Extract product name
            try:
                name_elem = product.find_element(By.XPATH,
                                                 './/div[contains(@class, "product-tile__name") and @itemprop="name"]')
                name = name_elem.text.strip() if name_elem else "Brak nazwy"
            except Exception as e:
                logger.warning(f"Product name not found: {e}")
                name = "Brak nazwy"

            # Extract packaging details
            try:
                packaging_elem = product.find_element(By.XPATH, './/div[contains(@class, "packaging-details")]')
                packaging_details = packaging_elem.text.strip() if packaging_elem else "Brak masy"
            except Exception as e:
                logger.warning(f"Packaging details not found: {e}")
                packaging_details = "Brak masy"

            logger.debug(f"Processing product: {name} - {packaging_details}")

            # Check for promotion
            try:
                promotion_elem = product.find_element(By.CLASS_NAME, "price-tile__label")
                promotion = promotion_elem.text.strip() if promotion_elem else "Brak promocji"
            except NoSuchElementException:
                promotion = "Brak promocji"

            # Check promotion date
            try:
                promo_dates_elem = product.find_element(By.CLASS_NAME, "product-details__info-item")
                promo_dates = promo_dates_elem.text.strip() if promo_dates_elem else "Brak daty promocji"
            except NoSuchElementException:
                promo_dates = "Brak daty promocji"

            # Get product URL
            try:
                product_url_elem = product.find_element(By.CLASS_NAME, "js-product-link")
                product_url = product_url_elem.get_attribute("href").strip() if product_url_elem else "Brak URL"
            except NoSuchElementException:
                product_url = "Brak URL"

            # Append product data, including its category
            data_list.append({
                "Kategoria": category,
                "Nazwa": name,
                "Masa": packaging_details,
                "Promocja": promotion,
                "Data promocji": promo_dates,
                "Data pobrania": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "URL": product_url
            })

            logger.info(f"Scraped product: {name}")

        except Exception as e:
            logger.error(f"Error retrieving product data: {e}")

    return True


# Create folder for results
output_folder = "results"
os.makedirs(output_folder, exist_ok=True)

# Iterate over each subsite category
for category in subsites:
    logger.info(f"Starting scraping for category: {category}")
    category_data = []
    page_number = 1
    subsite_url = f"{base_url}/{category}"

    while True:
        page_url = f"{subsite_url}/?page={page_number}"
        logger.info(f"Scraping category: {category}, page: {page_number}")

        if page_number == 1:
            success = scrape_page(page_url, first_page=True, category=category, data_list=category_data)
        else:
            success = scrape_page(page_url, category=category, data_list=category_data)

        if not success:
            logger.error(f"Scraping aborted for category '{category}' at page {page_number}.")
            break

        if not has_next_page():
            logger.info(f"Last page reached for category: {category}")
            break

        page_number += 1
        logger.debug(f"Moving to next page: {page_number} for category: {category}")

    # Save results for this category to a CSV file
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = os.path.join(output_folder, f"{category}_{current_timestamp}.csv")
    with open(csv_filename, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file,
                                fieldnames=["Kategoria", "Nazwa", "Masa", "Promocja", "Data promocji", "Data pobrania",
                                            "URL"])
        writer.writeheader()
        writer.writerows(category_data)

    logger.info(f"Results for category '{category}' saved to CSV file: {csv_filename}")

driver.quit()
logger.info("Browser closed successfully.")

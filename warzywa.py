import csv
import datetime
import os
import time
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up logging
log_folder = "log/warzywa"
os.makedirs(log_folder, exist_ok=True)
log_filename = os.path.join(log_folder, f"scraping_log_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Firefox and Geckodriver configuration
service = Service("/usr/local/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)

# List to store results
data_list = []

# Function to check if there is a "next" button (next page)
def has_next_page():
    try:
        # Check if there is a "next" button for the next page
        next_button = driver.find_element(By.CSS_SELECTOR, "a.bucket-pagination__icon.bucket-pagination__icon--next")
        return True
    except NoSuchElementException:
        # If the button does not exist, it means we are on the last page
        return False

# Function to scrape a single page
def scrape_page(page_url):
    driver.get(page_url)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    try:
        # Wait for product elements to load (specifically wait for at least 1 product on the page)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-grid__item"))
        )
    except TimeoutException:
        logging.error(f"Czas oczekiwania na załadowanie strony {page_url} upłynął.")
        return False

    # Get the products on the page
    products = driver.find_elements(By.CLASS_NAME, "product-grid__item")
    if not products:
        logging.warning(f"Brak produktów na stronie {page_url}. Kończenie scrapowania.")
        return False

    logging.info(f"Znaleziono {len(products)} produktów na stronie {page_url}.")

    for product in products:
        try:
            # Use XPath to more precisely locate the elements
            name = product.find_element(By.XPATH,
                                        './/div[contains(@class, "product-tile__name") and @itemprop="name"]').text.strip() if product.find_element(
                By.XPATH, './/div[contains(@class, "product-tile__name") and @itemprop="name"]') else "Brak nazwy"
            packaging_details = product.find_element(By.XPATH,
                                                     './/div[contains(@class, "packaging-details")]').text.strip() if product.find_element(
                By.XPATH, './/div[contains(@class, "packaging-details")]') else "Brak masy"

            logging.debug(f"Sprawdzam produkt: {name} - {packaging_details}")

            try:
                # Checking for promotion
                promotion = product.find_element(By.CLASS_NAME,
                                                 "price-tile__label").text.strip() if product.find_element(
                    By.CLASS_NAME, "price-tile__label") else "Brak promocji"
            except NoSuchElementException:
                promotion = "Brak promocji"

            try:
                # Checking promotion date
                promo_dates = product.find_element(By.CLASS_NAME,
                                                   "product-details__info-item").text.strip() if product.find_element(
                    By.CLASS_NAME, "product-details__info-item") else "Brak daty promocji"
            except NoSuchElementException:
                promo_dates = "Brak daty promocji"

            try:
                # Get product URL
                product_url = product.find_element(By.CLASS_NAME, "js-product-link").get_attribute(
                    "href").strip() if product.find_element(By.CLASS_NAME, "js-product-link") else "Brak URL"
            except NoSuchElementException:
                product_url = "Brak URL"

            # Add data to the results list
            data_list.append({
                "Nazwa": name,
                "Masa": packaging_details,
                "Promocja": promotion,
                "Data promocji": promo_dates,
                "Data pobrania": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "URL": product_url
            })

        except Exception as e:
            logging.error(f"Problem z pobraniem danych produktu: {e}")

    return True


# Starting URL
base_url = "https://zakupy.biedronka.pl/warzywa"

# Start scraping from page 1
page_number = 1
while True:
    logging.info(f"Scraping page {page_number}...")
    page_url = f"{base_url}/?page={page_number}"

    # Scrape the page
    if not scrape_page(page_url):
        break

    # Check if there is a "next" button for the next page
    if not has_next_page():
        logging.info("Osiągnięto ostatnią stronę.")
        break

    # Increase the page number
    page_number += 1

# Close the browser
driver.quit()

# Create folder for results
output_folder = "wyniki/warzywa"
os.makedirs(output_folder, exist_ok=True)

# Create a unique filename for the CSV file
current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
csv_filename = os.path.join(output_folder, f"warzywa_{current_timestamp}.csv")

# Save to CSV file
with open(csv_filename, mode="w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=["Nazwa", "Masa", "Promocja", "Data promocji", "Data pobrania", "URL"])
    writer.writeheader()
    writer.writerows(data_list)

logging.info(f"Wyniki zapisano do pliku {csv_filename}")

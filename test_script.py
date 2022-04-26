import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from smsactivate.api import SMSActivateAPI
from webdriver_manager.chrome import ChromeDriverManager

sms_active_api_key = "4233ddb81bb6e7718A274fce1cbAc2e5"

sms_api = SMSActivateAPI(sms_active_api_key)
sms_api.debug_mode = True
# service = ChromeService(executable_path=ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument("--window-size=1920,1080")
# options.add_argument("--ignore-certificate-errors")
# options.add_argument("--incognito")
# options.add_argument("headless")
# driver = webdriver.Chrome(service=service, chrome_options=options)
# driver.get(url="https://web.telegram.org/")
# driver.maximize_window()
# time.sleep(5)
# login_by_phone_number = WebDriverWait(driver, 10).until(
#     EC.presence_of_element_located((By.XPATH, "//button[text()[contains(., 'by phone Number')]]"))
# )
# login_by_phone_number.click()

number = sms_api.getNumber(service="tg", country=10, verification="true")

phone_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "sign-in-phone-number")))
phone_field.clear()
phone_field.send_keys(number["phone"])
checkbox_check = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//*[text()[contains(., 'signed in')]]"))
)
if checkbox_check.is_selected():
    checkbox_remember = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//label[@class='Checkbox']"))
    )

    checkbox_remember.click()

next_button = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//button[@class='btn-primary btn-color-primary rp']"))
)
next_button.click()

unique_links = set()
height_counter = 0
current_height = 0
previous_current_height = 0
wait = WebDriverWait(driver, 20)
while True:
    item = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[@role='gridcell']//div//article//a"))
    )
    # Scroll down to the bottom.
    if current_height:
        previous_current_height = current_height
    current_height = driver.execute_script("return document.body.scrollHeight;")
    if current_height == previous_current_height:
        break
    while True:
        height_counter += 300
        if height_counter >= current_height:
            break
        ## Should be retry here
        try:
            for element in wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@role='gridcell']//div//article//a"))
            ):
                href_element = element.get_attribute("href")
                if "collection" not in element.get_attribute("href"):
                    unique_links.add(href_element)
        except:
            for element in wait.until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[@role='gridcell']//div//article//a"))
            ):
                href_element = element.get_attribute("href")
                if "collection" not in element.get_attribute("href"):
                    unique_links.add(href_element)
        driver.execute_script(f"window.scrollTo(0, {height_counter});")
        time.sleep(2)

    # Wait to load the page.
    # WebDriverWait(driver, 30).until(
    #     EC.visibility_of_all_elements_located((By.XPATH, "//div[@role='gridcell']//div//article//a"))
    # )
    # time.sleep(3)
    # soup_a = BeautifulSoup(driver.page_source, "lxml")
    # Calculate new scroll height and compare with last scroll height.
    # new_height = driver.execute_script("return document.body.scrollHeight")
    # grid_cells_temp = []
    # grid_cells_temp = driver.find_elements_by_xpath("//div[@role='gridcell']//div//article//a")
    # grid_cells.extend(
    #     [
    #         grid_cell.get_attribute("href")
    #         for grid_cell in grid_cells_temp
    #         if "collection" not in grid_cell.get_attribute("href")
    #     ]
    # )
    # if new_height == last_height:

    #     break

    # last_height = new_height
print("Wait here")

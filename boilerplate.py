from smsactivate.api import SMSActivateAPI

# This sample code uses the Appium python client v2
# pip install Appium-Python-Client
# Then you can paste this into a file and simply run with Python
from appium.webdriver.appium_service import AppiumService
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
import time

appium_service = AppiumService()
appium_service.start(args=["-p 4723"])
caps = {}
caps["platformName"] = "Android"
caps["appium:deviceName"] = "R58M15BQNMH"
caps["appium:ensureWebviewsHavePages"] = True
caps["appium:nativeWebScreenshot"] = True
caps["appium:newCommandTimeout"] = 10000
caps["appium:connectHardwareKeyboard"] = True

driver = webdriver.Remote("http://localhost:4723/wd/hub", caps)

sms_active_api_key = "4233ddb81bb6e7718A274fce1cbAc2e5"
sms_api = SMSActivateAPI(sms_active_api_key)
number = sms_api.getNumber(service="tg", country=10, verification="true")


start_messaging_elem = driver.find_element_by_android_uiautomator('new UiSelector().textContains("Start Messaging")')
start_messaging_elem.click()
time.sleep(3)

el5 = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Country code")
el5.clear()
phone_number = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Phone number")
phone_number.clear()
el5.send_keys(number["phone"])
el6 = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Done")
el6.click()

# yes or no
try:
    pop_up = driver.find_element_by_android_uiautomator('new UiSelector().textContains("Yes")')
    pop_up.click()
except:
    pass

time.sleep(25)
sms_code_elem = driver.find_element(
    by=AppiumBy.XPATH,
    value="//android.widget.EditText[@index=0]",
)
status = sms_api.getStatus(number["activation_id"]).split(":")[1]
sms_code_elem.click()
sms_code_elem.send_keys(status)

time.sleep(5)
first_name = driver.find_element(
    by=AppiumBy.XPATH,
    value="//android.widget.FrameLayout[@index=0]//android.widget.EditText",
)

first_name.click()
first_name.send_keys("Dang")
last_name = driver.find_element(
    by=AppiumBy.XPATH,
    value="//android.widget.FrameLayout[@index=3]//android.widget.FrameLayout[@index=1]//android.widget.EditText",
)
last_name.click()
last_name.send_keys("Son")
complete_name_part = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Done")
complete_name_part.click()
time.sleep(10)
# el15 = driver.find_element(
#     by=AppiumBy.CLASS_NAME,
#     value="/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.TextView[2]",
# )
# el15.click()
# el16 = driver.find_element(by=AppiumBy.ID, value="com.android.permissioncontroller:id/permission_allow_button")
# el16.click()
# access to contacts
try:
    pop_up_access_contacts = driver.find_element_by_android_uiautomator('new UiSelector().textContains("CONTINUE")')
    pop_up_access_contacts.click()
    time.sleep(4)
    allow_contacts = driver.find_element(AppiumBy.XPATH, "//android.widget.Button[@text='Allow']")
    allow_contacts.click()
except:
    pass

# logout
time.sleep(4)
el19 = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Open navigation menu")
el19.click()
time.sleep(3)
settings_elem = driver.find_element(
    by=AppiumBy.XPATH,
    value="//android.widget.TextView[@text='Settings']",
)
settings_elem.click()
more_opts = driver.find_element(
    by=AppiumBy.XPATH, value="//android.widget.ImageButton[@content-desc='More options']//android.widget.ImageView"
)
more_opts.click()
logout_elem = driver.find_element(
    by=AppiumBy.XPATH,
    value="//android.widget.TextView[@text='Log out']",
)
logout_elem.click()
time.sleep(4)
logout_main = driver.find_element(
    by=AppiumBy.XPATH,
    value="//androidx.recyclerview.widget.RecyclerView//android.widget.FrameLayout[7]//android.widget.TextView[@text='Log Out']",
)
logout_main.click()
time.sleep(2)
logout_popup = driver.find_element(
    by=AppiumBy.XPATH,
    value="//android.widget.TextView[@text='LOG OUT']",
)
logout_popup.click()

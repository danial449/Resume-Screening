from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import time
from dotenv import load_dotenv
import os

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  
options.add_argument("--disable-blink-features=AutomationControlled")  

driver = webdriver.Chrome(options=options)
load_dotenv()
linkedin_username = os.getenv("EMAIL")  
linkedin_password = os.getenv("PASSWORD")  #

login_url = "https://www.linkedin.com/login"

driver.get(login_url)

time.sleep(3)

email_input = driver.find_element(By.ID, "username")
email_input.send_keys(linkedin_username)

password_input = driver.find_element(By.ID, "password")
password_input.send_keys(linkedin_password)

password_input.send_keys(Keys.RETURN)

time.sleep(5)

profile_url = "https://www.linkedin.com/in/lyleompad"
driver.get(profile_url)

time.sleep(5)
name = driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/div/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[1]/div[1]/span/a/h1').text.strip()
heading = driver.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[1]/div[2]').text.strip()
location = driver.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[1]/div[2]/div[2]/div[2]/span[1]').text.strip()
experiences = driver.find_elements(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul')

extracted_experience = []
for exp in experiences:
    try:
        title = exp.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul/li[1]/div/div[2]/div[1]/div/div/div/div/div/span[1]').text.strip()
        company = exp.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul/li[1]/div/div[2]/div[1]/div/span[1]/span[1]').text.strip()
        total_expereince = exp.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section[3]/div[3]/ul/li[1]/div/div[2]/div[1]/div/span[2]/span[1]').text.strip()
        extracted_experience.append({"title": title, "total_experience": total_expereince, "company": company})
    except Exception as e:
        print(f"Error extracting experience: {e}")
response = {
    "name" : name,
    "heading" : heading,
    "location" : location,
    "experience" : extracted_experience

}
print(response)
driver.quit()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def get_linkedin_cookies(email, password):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get("https://www.linkedin.com/login")
        time.sleep(2)

        # Enter email
        email_field = driver.find_element(By.ID, "username")
        email_field.send_keys("bazaarzo.com@gmail.com")

        # Enter password
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys("pakistanzindabad123449")
        password_field.send_keys(Keys.RETURN)

        time.sleep(5)  # Allow time for login

        cookies = driver.get_cookies()
        driver.quit()
        
        # Extract "li_at" cookie (LinkedIn session cookie)
        li_at_cookie = next((cookie['value'] for cookie in cookies if cookie['name'] == 'li_at'), None)

        return li_at_cookie
    
    except Exception as e:
        driver.quit()
        print("Error logging in:", str(e))
        return None

# Run and print cookie
if __name__ == "__main__":
    email = "your-email@example.com"
    password = "your-password"
    cookie = get_linkedin_cookies(email, password)
    if cookie:
        print("Session Cookie:", cookie)
    else:
        print("Failed to retrieve session cookie.")

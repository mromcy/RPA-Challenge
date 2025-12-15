from playwright.sync_api import sync_playwright
import pandas as pd 
import time


file = pd.read_excel('challenge.xlsx')

with sync_playwright() as p:
    # Launch the browser
    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
    page = browser.new_page(no_viewport=True)
    page.goto("https://rpachallenge.com/")
    
    # Start the challenge
    page.get_by_role("button", name="Start").click()

    # Fill the form using data from the xlsx file
    for i, row in file.iterrows():
        page.locator("//label[text()='First Name']/following-sibling::input").fill(str(row['First Name']))
        page.locator("//label[text()='Last Name']/following-sibling::input").fill(str(row['Last Name']))
        page.locator("//label[text()='Company Name']/following-sibling::input").fill(str(row['Company Name']))
        page.locator("//label[text()='Role in Company']/following-sibling::input").fill(str(row['Role in Company']))
        page.locator("//label[text()='Address']/following-sibling::input").fill(str(row['Address']))
        page.locator("//label[text()='Email']/following-sibling::input").fill(str(row['Email']))
        page.locator("//label[text()='Phone Number']/following-sibling::input").fill(str(row['Phone Number']))
        page.get_by_role("button", name="Submit").click()

    time.sleep(5)
    browser.close()







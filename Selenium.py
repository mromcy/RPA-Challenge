from selenium import webdriver
from selenium.webdriver.common.by import By
import time 
import pandas as pd

file = pd.read_excel('challenge.xlsx')

# Launch the browser
driver = webdriver.Chrome()
driver.maximize_window()
driver.get('https://rpachallenge.com/')

#start challenge
driver.find_element(By.XPATH, '/html/body/app-root/div[2]/app-rpa1/div/div[1]/div[6]/button').click()

# Fill the form using data from the xlsx file
for index, row in file.iterrows():
    driver.find_element(By.XPATH, "//label[text()='First Name']/following-sibling::input").send_keys(str(row['First Name']))
    driver.find_element(By.XPATH, "//label[text()='Last Name']/following-sibling::input").send_keys(str(row['Last Name']))
    driver.find_element(By.XPATH, "//label[text()='Company Name']/following-sibling::input").send_keys(str(row['Company Name']))
    driver.find_element(By.XPATH, "//label[text()='Role in Company']/following-sibling::input").send_keys(str(row['Role in Company']))
    driver.find_element(By.XPATH, "//label[text()='Address']/following-sibling::input").send_keys(str(row['Address']))
    driver.find_element(By.XPATH, "//label[text()='Email']/following-sibling::input").send_keys(str(row['Email']))
    driver.find_element(By.XPATH, "//label[text()='Phone Number']/following-sibling::input").send_keys(str(row['Phone Number']))
    driver.find_element(By.XPATH, '//input[@type="submit" and @value="Submit"]').click()
   
time.sleep(5)
driver.close()


    

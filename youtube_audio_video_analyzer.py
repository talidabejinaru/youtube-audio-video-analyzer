#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import sys
import random


# Check if the video name is provided for the search
if len(sys.argv) < 2:
    print("Please enter a video name")
    sys.exit(1)

# The video name from the command-line arguments
video_name = " ".join(sys.argv[1:])

# Initialize the driver for Firefox 
driver_path = "/home/talida/Desktop/AROBS/geckodriver"
driver = webdriver.Firefox(executable_path=driver_path) 

# Maximizing the browser window
driver.maximize_window()

# Navigate to YouTube
url = "https://www.youtube.com"
driver.get(url)

time.sleep(5)  # Waits for the page to load completely

try:
    # Search for accept button
    accept_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept all') or contains(., 'Accept')]"))
    )
    accept_button.click()
    print("The cookie popup was successfully closed!")

except Exception as e:
    print(f"No cookie popup found or an error occurred: {e}")


# Find the search bar and search for a video
search_box = driver.find_element(By.NAME, "search_query")
search_box.send_keys(video_name)
search_box.send_keys(Keys.RETURN)

# Waits for the results to load
WebDriverWait(driver, 10).until(
    EC.presence_of_all_elements_located((By.XPATH, "//a[@id='video-title']"))
)

# Find a random video in the results and click on it
try:
    
    videos = driver.find_elements(By.XPATH, "//a[@id='video-title']")
    random_video = random.choice(videos)  
    random_video.click()
    
except Exception as e:
    print("No results found.")

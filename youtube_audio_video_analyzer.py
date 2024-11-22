#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
import time
import sys
import random
import numpy as np
import cv2
import threading
import pyautogui
import soundcard as sc
import soundfile as sf
import ffmpeg
import os
import logging
import socket
import scipy.io.wavfile as wav
import csv
import requests


# Global variables
RECORDING_TIME_IN_SEC = 120 # Time duration for recording
stop_threads = threading.Event() # Synchronization event for thread control

# Path to the geckodriver executable
driver_path = "/home/talida/Desktop/AROBS/geckodriver"

# Set up the log configuration
logging.basicConfig(
    filename='log_file.log',
    filemode='w',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Check if the video name is provided as a command-line argument
if len(sys.argv) < 2:
    print("Please enter a video name")
    sys.exit(1)

# Combine arguments into a single video name string
search_arg = " ".join(sys.argv[1:])


class Executer:
    """
    Coordinates browser automation to play a random video, record audio and video
    and analyze the audio file
    """

    def __init__(self, audio_record, video_record):
        """
        Initializes the Executer class with instances of AudioRecord and VideoRecord.
        """
        # Accept instances of AudioRecord and VideoRecord as parameters
        self.audio_record = audio_record
        self.video_record = video_record
        self.audio_name = "audio.wav" # Default audio filename
        self.video_name = "video.mp4" # Default video filename
        self.audio_levels = "audio_levels.csv" # Default CSVfile for audio levels
        # Create an instance of Options to configure the browser settings
        options = Options()
        options.headless = False # Open the browser window (not headless)
        self.driver = webdriver.Firefox(executable_path=driver_path, options=options) # Selenium WebDriver instance


    def clean_up(self):
        """
        Cleans up temporary files (audio, video and audio level CSV)
        """
        logging.info("Starting cleanup process...")
        try:
            # Delete the audio file if it exists
            if os.path.exists(self.audio_name):
                logging.info(f"Try to delete audio file: {self.audio_name}")
                os.remove(self.audio_name)
                logging.info(f"Audio file has been deleted")
            else:
                logging.info(f"Audio file does not exist: {self.audio_name}")

            # Delete the video file if it exists
            if os.path.exists(self.video_name):
                logging.info(f"Try to delete video file: {self.video_name}")
                os.remove(self.video_name)
                logging.info(f"Video file has been deleted")
            else:
                logging.info(f"Video file does not exist: {self.video_name}")

            # Delete the audio levels CSV if it exists
            if os.path.exists(self.audio_levels):
                logging.info(f"Try to delete audio_levels CSV file: {self.audio_levels}")
                os.remove(self.audio_levels)
                logging.info(f"Audio_levels CSV file has been deleted")
            else:
                logging.info(f"Audio levels CSV file does not exist: {self.audio_levels}")
        
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


    @staticmethod
    def check_internet_connection(host="8.8.8.8", port=53, timeout=5):
        """
        Checks if an internet connection is available by pinging a host
        """
        logging.info("Checking internet connectivity...")
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            logging.info(f"Internet connection is available")
            return True
        except socket.error as ex:
            logging.error(f"Network error: {ex}")
            return False


    def open_url_with_retry(self, url, retries=5, wait_time=15):
        """
        Tries to open a URL with retry logic in case of failure
        Retries a specified number of times if the page fails to load
        """
        attempt = 0
        while attempt < retries:
            try:
                # Trying to load the URL
                logging.info(f"Attempting to load URL {url} (Attempt {attempt + 1}/{retries})")
                self.driver.get(url)
                logging.info(f"Page loaded successfully ({attempt + 1}/{retries}).")
                return True 
            except (TimeoutException, WebDriverException) as e:
                 # Exception in case of a timeout or driver-related issue 
                logging.error(f"Error loading page: {e}")
                attempt += 1  
                if attempt < retries:  
                    logging.info(f"Retrying... ({attempt}/{retries})")
                time.sleep(wait_time) 
            except Exception as e:
                # Unexpected errors 
                logging.error(f"An unexpected error occurred: {e}")
                break

        # If all retry attempts fail and the page is still not loaded
        logging.error(f"Unable to load the page after {retries} attempts.")
        return False



    def close_popup_if_present(self):
        """
        Checks if a pop-up is present and tries to close it
        """
        try:
            popup_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'No thanks') or contains(., 'Accept all') or contains(., 'Accept')]"))
            )
            popup_button.click()
            logging.info("Pop-up has been closed")
        except Exception as e:
            logging.info(f"No pop-up found or an error occurred: {e}")



    def play_random_video(self, video_name):
        """
        Automates the process of opening a browser, searching for a random video on YouTube, 
        and recording video and audio
        """
        start_time = time.time()

        
        try:
            logging.info(f"Launching browser using driver at {driver_path}")

            self.driver.set_page_load_timeout(30) # Set page load timeout
            
            self.driver.maximize_window() # Maximizing the browser window

            # Navigate to YouTube
            url = "https://www.youtube.com"
            try:
                logging.info(f"Navigating to {url}")
                self.driver.get(url)
                WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable((By.XPATH, "//input[@id='search']")))
                logging.info("YouTube loaded successfully")
                time.sleep(15)
            except Exception as e:
                # Retry mechanism if YouTube page fails to load
                logging.error(f"Error loading YouTube: {e}. Retrying...")
                time.sleep(8)
                if not self.open_url_with_retry(url, retries=3, wait_time=5):
                    logging.error(f"Unable to access {url} after multiple retries")
                    raise Exception("Cannot access YouTube after multiple retries")
                     

            time.sleep(8)  # Waits for the page to load completely
            
            # Close any pop-ups that might appear as soon as YouTube is loaded
            self.close_popup_if_present()

            try:
                # Find the search bar and search for a video
                logging.info(f"Trying to search a video: {video_name}")
                search_box = self.driver.find_element(By.NAME, "search_query")
                logging.info(f"Found the search bar")
                search_box.send_keys(video_name)
                logging.info(f"Entered '{video_name}' into the search bar")
                search_box.send_keys(Keys.RETURN)
                logging.info(f"Pressed enter")
            except Exception as e:
                logging.error(f"Error occurred while searching for the video: {e}")

            # Waits for the results to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[@id='video-title']"))
            )

            # Find a random video in the results and click on it
            try:
                logging.info(f"Selecting a random video from the results")
                videos = self.driver.find_elements(By.XPATH, "//a[@id='video-title']")
                random_video = random.choice(videos)  
                random_video.click()
                logging.info(f"A random video has been selected")

            except Exception as e:
                logging.error("No results found or error occurred during video selection.")

            # Move the cursor over the video fullscreen button and click on it
            logging.info("Trying to click the fullscreen button")
            try:
                fullscreen_button = WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.ytp-fullscreen-button")))

                ActionChains(self.driver).move_to_element(fullscreen_button).perform()
                fullscreen_button.click()
                logging.info("Fullscreen button clicked successfully")
            except ElementNotInteractableException as e:
                logging.warning(f"Error interacting with fullscreen button: {e}")
            
        
            # Wait or close after RECORDING_TIME_IN_SEC seconds
            while time.time() - start_time < RECORDING_TIME_IN_SEC and not stop_threads.is_set():
                self.close_popup_if_present()  # Close pop-ups if they appear
                time.sleep(1)
        except Exception as e:
            self.driver.quit()
            logging.error(f"An error occurred during the YouTube video play process: {e}")
            sys.exit(1)

        finally:
            # Ensure the browser is closed after the process completes
            if self.driver:
                logging.info("Quitting the browser")
                self.driver.quit()


    def execute(self):
        """
        Main execution method for starting the recording process
        - Cleans up resources
        - Checks internet connection
        - Starts threads for YouTube video playing, audio and video
        - Stops the threads after a specified time
        - Analyzes the audio file
        """
        self.clean_up()
        logging.info("Cleanup has been completed")

        # Check network connectivity
        logging.info("Checking network connectivity...")
        if not self.check_internet_connection():
            logging.error("Network is unavailable")
            self.driver.quit()
            sys.exit(1)

        # Create and start threads with the instance methods as targets
        youtube_thread = threading.Thread(target=self.play_random_video, args=(search_arg,))
        video_thread = threading.Thread(target=self.video_record.record_video)
        audio_thread = threading.Thread(target=self.audio_record.record_audio)

        youtube_thread.start()
        logging.info("Youtube thread started")
        video_thread.start()
        logging.info("Video recording thread started")
        audio_thread.start()
        logging.info("Audio recording thread started")

        # Wait for the specified time before stopping
        logging.info(f"Waiting for {RECORDING_TIME_IN_SEC} seconds before stopping threads")
        time.sleep(RECORDING_TIME_IN_SEC)
        stop_threads.set()  # Signal all threads to stop
        logging.info("All threads have finished execution")

        youtube_thread.join()
        video_thread.join()
        audio_thread.join()


        # Analyze audio file if exists
        if os.path.exists("audio.wav"):
            logging.info("Audio file does exist. Initiating analysis.")
            AudioRecord.analyze_audio_file("audio.wav")
        else:
            logging.error("Audio file does not exist. Skipping analysis.")


class AudioRecord:
    """
    Handles the recording and analysis of audio from a microphone
    """

    OUTPUT_FILE_NAME = "audio.wav"
    SAMPLE_RATE = 48000
    CHUNK_SIZE = 1024  # Capture audio in smaller chunks for better handling

    def record_audio(self):
        """
        Records audio from the default microphone and saves it to a file.
        - Captures audio in chunks of size "CHUNK_SIZE"
        - Saves the audio data as a ".wav" file
        """
        # Select the default microphone with loopback
        default_mic = sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True) 
        
        if default_mic is None:
            logging.error("Could not find a suitable microphone for recording")
            return

        audio_data = []

        # Start recording with the microphone
        logging.info("Starting audio recording")
        with default_mic.recorder(samplerate=self.SAMPLE_RATE) as mic:
            start_time = time.time()

            while time.time() - start_time < RECORDING_TIME_IN_SEC and not stop_threads.is_set():
                chunk = mic.record(numframes=self.CHUNK_SIZE)
                audio_data.append(chunk[:, 0])

        # Concatenate all captured audio chunks and save to file
        if audio_data:
            logging.info("Audio recording has been completed")
            full_data = np.concatenate(audio_data, axis=0)
            sf.write(file=self.OUTPUT_FILE_NAME, data=full_data, samplerate=self.SAMPLE_RATE)
            logging.info(f"Audio saved to {self.OUTPUT_FILE_NAME}")
        else:
            logging.error("No audio data captured")

    @staticmethod
    def analyze_audio_file(audio_filename, output_filename="audio_levels.csv"):
        """
        Analyzes the audio file and calculates the average sound level in dB
        - Reads the audio data from a ".wav" file.
        - Computes RMS value and converts it to dB SPL for the entire file.
        - Saves the result in a CSV file with the average sound level.
        """
        # Read the WAV audio file
        sample_rate, data = wav.read(audio_filename)

        # Extract audio data
        if len(data.shape) > 1:
            data = data[:, 0]  

        # Normalize audio data to the range [-1, 1]
        data = data / np.max(np.abs(data))

        # Calculate the RMS value for the entire audio file
        rms = np.sqrt(np.mean(data**2))

        # Convert RMS to dB (SPL - Sound Pressure Level)
        p0 = 20e-6 
        spl = 20 * np.log10(rms / p0) if rms > 0 else -np.inf

        # Save the result to a CSV file
        with open(output_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Average Sound Level (dB)"])
            writer.writerow([spl])

        logging.info(f"Audio analysis saved to {output_filename}")


class VideoRecord:
    """
    Handles the recording of the screen and saving it as a video file
    """

    OUTPUT_FILE_NAME = "video.mp4"
    SCREEN_SIZE = tuple(pyautogui.size())

    def save_video(self, frames, screen_size, fps):
        """
        Saves a series of frames as a video file
        - Uses OpenCV to write frames to a ".mp4" video file
        """
        logging.info(f"Trying to save video")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(self.OUTPUT_FILE_NAME, fourcc, fps, screen_size)

        for frame in frames:
            video_writer.write(frame)

        video_writer.release()
        logging.info(f"Video saved to {self.OUTPUT_FILE_NAME}")


    def record_video(self):
        """
        Records the screen and saves the video
        - Captures screenshots at regular intervals
        - Stores the frames and saves them to a ".mp4" video file
        """
        logging.info("Starting video recording.")
        frames = []
        timestamps = []

        start_time = time.time()
        logging.info(f"Recording video for {RECORDING_TIME_IN_SEC} seconds...")

        while time.time() - start_time < RECORDING_TIME_IN_SEC and not stop_threads.is_set():
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame)
            timestamps.append(time.time() - start_time)

        # Calculate dynamic FPS based on captured frames and time
        duration = timestamps[-1] if timestamps else RECORDING_TIME_IN_SEC
        calculated_fps = len(frames) / duration if duration > 0 else 60.0
        logging.info(f"Recording completed")

        # Save the frames to a video file using calculated FPS
        self.save_video(frames, self.SCREEN_SIZE, calculated_fps)
        logging.info("Video recording and saving process completed")


if __name__ == "__main__":
    # Instantiate AudioRecord and VideoRecord before passing to Executer
    audio_record = AudioRecord()
    video_record = VideoRecord()

    # Pass instances to Executer
    executer = Executer(audio_record, video_record)

    executer.execute()
    logging.info("The script was executed")
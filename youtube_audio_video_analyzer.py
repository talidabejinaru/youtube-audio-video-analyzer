#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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
from selenium.webdriver.firefox.options import Options

# Global variables
RECORDING_TIME_IN_SEC = 120
stop_threads = threading.Event()

driver_path = "/home/talida/Desktop/AROBS/geckodriver"

# Set up the log configuration
logging.basicConfig(
    filename='log_file.log',
    filemode='w',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Check if the video name is provided for the search
if len(sys.argv) < 2:
    print("Please enter a video name")
    sys.exit(1)

# The video name from the command-line arguments
search_arg = " ".join(sys.argv[1:])

class Executer:

    def __init__(self, audio_record, video_record):
        # Accept instances of AudioRecord and VideoRecord as parameters
        self.audio_record = audio_record
        self.video_record = video_record
        self.audio_name = "audio.wav"
        self.video_name = "video.mp4"
        self.audio_levels = "audio_levels.csv"

    # Cleanup function for deleting temporary files
    def clean_up(self):
        logging.info("Starting cleanup process...")
        try:
            # Delete the audio file if it exists
            if os.path.exists(self.audio_name):
                logging.info(f"Try to delete audio file: {self.audio_name}")
                os.remove(self.audio_name)
                logging.info(f"Audio file has been deleted")
            else:
                logging.info(f"Audio file does not exist: {self.audio_name}")

            #Delete the video file if it exists
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

    # Check internet connection
    @staticmethod
    def check_internet_connection(host="8.8.8.8", port=53, timeout=5):
        logging.info("Checking internet connectivity...")
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            logging.info(f"Internet connection is available")
            return True
        except socket.error as ex:
            logging.error(f"Network error: {ex}")
            return False

    def play_random_video(self, video_name):
        start_time = time.time()
        driver = None
        
        try:
            logging.info(f"Launching browser using driver at {driver_path}")
             # Create an instance of Options to configure the browser settings
            options = Options()
            # It will open the browser window)
            options.headless = False 
            
            driver = webdriver.Firefox(executable_path=driver_path, options=options)

            driver.set_page_load_timeout(10) # Set the page load timeout
            
            # Maximizing the browser window
            driver.maximize_window()

            # Navigate to YouTube
            url = "https://www.youtube.com"
            try:
                logging.info(f"Navigating to {url}")
                driver.get(url)
            except Exception as e:
                logging.error(f"Error loading YouTube: {e}. Retrying...")
                time.sleep(8) 
                try:
                    driver.get(url)  # try again
                except Exception as e:
                    logging.error(f"Retry failed. Unable to access {url}: {e}")
                    raise Exception("Cannot access YouTube")

            time.sleep(8)  # Waits for the page to load completely

            try:
                # Search for accept button
                accept_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept all') or contains(., 'Accept')]"))
                )
                accept_button.click()
                logging.info("The cookie popup was successfully closed!")

            except Exception as e:
                logging.warning(f"No cookie popup found or an error occurred: {e}")

            # Find the search bar and search for a video
            logging.info(f"Searching for a video: {video_name}")
            search_box = driver.find_element(By.NAME, "search_query")
            logging.info(f"Found the search bar")
            search_box.send_keys(video_name)
            logging.info(f"Entered '{video_name}' into the search bar")
            search_box.send_keys(Keys.RETURN)
            logging.info(f"Pressed enter")

            # Waits for the results to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[@id='video-title']"))
            )

            # Find a random video in the results and click on it
            try:
                logging.info(f"Selecting a random video from the results")
                videos = driver.find_elements(By.XPATH, "//a[@id='video-title']")
                random_video = random.choice(videos)  
                random_video.click()
                logging.info(f"A random video has been selected")

            except Exception as e:
                logging.error("No results found or error occurred during video selection.")

            # Move the cursor over the video fullscreen button and click on it
            logging.info("Trying to click the fullscreen button")
            fullscreen_button = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.ytp-fullscreen-button")))

            ActionChains(driver).move_to_element(fullscreen_button).perform()
            fullscreen_button.click()
            logging.info("Fullscreen button clicked successfully")
        

            # Wait or close after RECORDING_TIME_IN_SEC seconds
            while time.time() - start_time < RECORDING_TIME_IN_SEC and not stop_threads.is_set():
                time.sleep(1)
        except Exception as e:
            logging.error(f"An error occurred during the YouTube video play process: {e}")
            if driver:
                logging.info("Closing browser due to error.")
                driver.quit()
            sys.exit(1)  # Close the script
        finally:
            if driver:
                logging.info("Quitting the browser")
                driver.quit()


    def execute(self):
        self.clean_up()
        logging.info("Cleanup has been completed")

        # Check network connectivity
        logging.info("Checking network connectivity...")
        if not self.check_internet_connection():
            logging.error("Network is unavailable")
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

    OUTPUT_FILE_NAME = "audio.wav"
    SAMPLE_RATE = 48000
    CHUNK_SIZE = 1024  # Capture audio in smaller chunks for better handling

    def record_audio(self):
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
                audio_data.append(chunk[:, 0])  # Use only the first channel

        # Concatenate all captured audio chunks and save to file
        if audio_data:
            logging.info("Audio recording has been completed")
            full_data = np.concatenate(audio_data, axis=0)
            sf.write(file=self.OUTPUT_FILE_NAME, data=full_data, samplerate=self.SAMPLE_RATE)
            logging.info(f"Audio saved to {self.OUTPUT_FILE_NAME}")
        else:
            logging.error("No audio data captured")

    @staticmethod
    def analyze_audio_file(audio_filename, output_filename="audio_levels.csv", chunk_duration_sec=1):
        # Read the WAV audio file
        sample_rate, data = wav.read(audio_filename)

        # Extract audio data (if the audio is stereo, take only one channel)
        if len(data.shape) > 1:
            data = data[:, 0]  # If stereo, take only the left channel

        # Normalize audio data to the range [-1, 1]
        data = data / np.max(np.abs(data))

        # Prepare the output CSV file
        with open(output_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Time (s)", "Sound Level (dB)"])  # Write the header to the CSV file

            # Process the audio file in chunks
            num_samples_per_chunk = int(sample_rate * chunk_duration_sec)
            num_chunks = len(data) // num_samples_per_chunk

            for i in range(num_chunks):
                # Extract a chunk of audio
                start_sample = i * num_samples_per_chunk
                end_sample = (i + 1) * num_samples_per_chunk
                chunk = data[start_sample:end_sample]

                # Calculate the RMS value for the chunk
                rms = np.sqrt(np.mean(chunk**2))

                # Convert RMS to dB (SPL - Sound Pressure Level)
                p0 = 20e-6  # Reference sound pressure level (in Pa)
                spl = 20 * np.log10(rms / p0) if rms > 0 else -np.inf

                # Write the sound level in dB and the timestamp (in seconds) to the CSV file
                time_in_seconds = i * chunk_duration_sec
                writer.writerow([time_in_seconds, spl])


        logging.info(f"Audio analysis saved to {output_filename}")


class VideoRecord:

    OUTPUT_FILE_NAME = "video.mp4"
    SCREEN_SIZE = tuple(pyautogui.size())

    def save_video(self, frames, screen_size, fps):
        logging.info(f"Trying to save video")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(self.OUTPUT_FILE_NAME, fourcc, fps, screen_size)

        for frame in frames:
            video_writer.write(frame)

        video_writer.release()
        logging.info(f"Video saved to {self.OUTPUT_FILE_NAME}")

    # Record the screen
    def record_video(self):
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
        calculated_fps = len(frames) / duration if duration > 0 else 24.0
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

    # Execute the script
    executer.execute()

    logging.info("Script execution completed")
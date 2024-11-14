#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

from selenium.webdriver.common.action_chains import ActionChains


# Global variables
RECORDING_TIME = 120
stop_threads = threading.Event()

# Check if the video name is provided for the search
if len(sys.argv) < 2:
    print("Please enter a video name")
    sys.exit(1)

# The video name from the command-line arguments
video_name = " ".join(sys.argv[1:])

# Initialize the driver for Firefox
driver_path = "/home/talida/Desktop/AROBS/geckodriver"

def play_random_video(video_name):
    start_time = time.time()

    driver = webdriver.Firefox(executable_path=driver_path)

    # Maximizing the browser window
    driver.maximize_window()

    # Navigate to YouTube
    url = "https://www.youtube.com"
    driver.get(url)

    time.sleep(15)  # Waits for the page to load completely

    try:
        # Search for accept button
        accept_button = WebDriverWait(driver, 20).until(
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
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.XPATH, "//a[@id='video-title']"))
    )

    # Find a random video in the results and click on it
    try:
        videos = driver.find_elements(By.XPATH, "//a[@id='video-title']")
        random_video = random.choice(videos)  
        random_video.click()
        
    except Exception as e:
        print("No results found.")

    # Move the cursor over the video fullscreen button and click on it
    fullscreen_button = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.ytp-fullscreen-button")))
    ActionChains(driver).move_to_element(fullscreen_button).perform()
    fullscreen_button.click()

    # Wait or close after RECORDING_TIME seconds
    while time.time() - start_time < RECORDING_TIME and not stop_threads.is_set():
        time.sleep(1)
    
    driver.quit()

# Record the screen
def record_video():
    SCREEN_SIZE = tuple(pyautogui.size())
    frames = []
    timestamps = []

    start_time = time.time()

    while time.time() - start_time <  RECORDING_TIME and not stop_threads.is_set():
        img = pyautogui.screenshot()
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)
        timestamps.append(time.time() - start_time)

    # Calculate dynamic FPS based on captured frames and time
    duration = timestamps[-1] if timestamps else RECORDING_TIME
    calculated_fps = len(frames) / duration if duration > 0 else 24.0

    # Save the frames to a video file using calculated FPS
    save_video(frames, SCREEN_SIZE, calculated_fps)

def save_video(frames, screen_size, fps):
    output_file = "video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(output_file, fourcc, fps, screen_size)

    for frame in frames:
        video_writer.write(frame)

    video_writer.release()
    print(f"Video saved to {output_file} with FPS: {fps}")

def record_audio():
    OUTPUT_FILE_NAME = "audio.wav"
    SAMPLE_RATE = 48000
    CHUNK_SIZE = 1024  # Capture audio in smaller chunks for better handling

    # Select the default microphone with loopback
    default_mic = sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
    
    if default_mic is None:
        print("Could not find a suitable microphone for recording.")
        return

    audio_data = []

    # Start recording with the microphone
    with default_mic.recorder(samplerate=SAMPLE_RATE) as mic:
        start_time = time.time()

        while time.time() - start_time < RECORDING_TIME and not stop_threads.is_set():
            chunk = mic.record(numframes=CHUNK_SIZE)
            audio_data.append(chunk[:, 0])  # Use only the first channel

    # Concatenate all captured audio chunks and save to file
    if audio_data:
        full_data = np.concatenate(audio_data, axis=0)
        sf.write(file=OUTPUT_FILE_NAME, data=full_data, samplerate=SAMPLE_RATE)
        print(f"Audio saved to {OUTPUT_FILE_NAME}")
    else:
        print("No audio data captured.")

def merge_video_audio(video_file, audio_file):
    if os.path.exists(video_file) and os.path.exists(audio_file):
        try:
            video = ffmpeg.input(video_file)
            audio = ffmpeg.input(audio_file)

            output_file = "output.mp4"
            ffmpeg.output(video, audio, output_file, vcodec='libx264', acodec='aac').run()
            print(f"Video and audio merged successfully into {output_file}")

            # Remove the intermediate files
            os.remove(video_file)
            os.remove(audio_file)
            print("Intermediate files removed.")
            
        except ffmpeg.Error as e:
            print(f"Error occurred while merging video and audio: {e.stderr.decode()}")
    else:
        print("Missing video or audio files.")

if __name__ == "__main__":
    youtube_thread = threading.Thread(target=play_random_video, args=(video_name,))
    video_thread = threading.Thread(target=record_video)
    audio_thread = threading.Thread(target=record_audio)

    youtube_thread.start()
    video_thread.start()
    audio_thread.start()

    # Wait for RECORDING_TIME seconds before stopping
    time.sleep(RECORDING_TIME)
    stop_threads.set()  # Signal all threads to stop

    youtube_thread.join()
    video_thread.join()
    audio_thread.join()

    # Merge the video and audio files
    merge_video_audio("video.mp4", "audio.wav")

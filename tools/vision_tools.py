import os
import cv2
import numpy as np
import pyautogui
import time
from langchain_core.tools import tool


@tool
def record_screen(duration_seconds: int = 10, filename: str = "screen_recording.avi") -> str:
    """
    Records the primary screen for a specified duration in seconds and saves it as an AVI video file.
    Note: If running in Docker without X11 forwarding, this will record the headless container display.
    """
    try:
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)

        screen_size = tuple(pyautogui.size())
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(filepath, fourcc, 20.0, screen_size)

        start_time = time.time()
        while int(time.time() - start_time) < duration_seconds:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out.write(frame)

        out.release()
        return f"Successfully recorded screen for {duration_seconds} seconds. Saved to {filepath}"
    except Exception as e:
        return f"Failed to record screen: {str(e)}"

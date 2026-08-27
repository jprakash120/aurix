import os
import time
import cv2
import win32com.client

from google import genai
from google.genai import types


# -----------------------------------
# AURIX VISION CONFIGURATION
# -----------------------------------

IMAGE_FILE = "aurix_vision.jpg"

VISION_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


# -----------------------------------
# API KEY CHECK
# -----------------------------------

if not os.getenv("GEMINI_API_KEY"):
    print("ERROR: GEMINI_API_KEY is missing.")
    print('Set it with: setx GEMINI_API_KEY "your_key_here"')
    exit()


client = genai.Client()


# -----------------------------------
# AURIX VOICE
# -----------------------------------

try:
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    speaker.Rate = 0
    speaker.Volume = 100
except Exception:
    speaker = None


def speak(text):
    if speaker:
        try:
            speaker.Speak(text)
        except Exception:
            pass


# -----------------------------------
# CAMERA CAPTURE
# -----------------------------------

def capture_image():
    print("\nAURIX: Activating vision...")
    speak("Activating vision.")

    # CAP_DSHOW usually opens Windows webcams faster
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    # Fallback if DirectShow does not work
    if not camera.isOpened():
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError(
            "I could not access the camera. "
            "Check Windows camera permissions."
        )

    # Give webcam time to adjust exposure/focus
    time.sleep(1)

    # Read a few frames so we don't use the first dark frame
    frame = None

    for _ in range(5):
        success, frame = camera.read()

    camera.release()

    if not success or frame is None:
        raise RuntimeError("Camera opened, but I could not capture an image.")

    # Save the image so you can inspect what AURIX saw
    cv2.imwrite(IMAGE_FILE, frame)

    # Convert image to JPEG bytes for Gemini
    success, encoded_image = cv2.imencode(".jpg", frame)

    if not success:
        raise RuntimeError("I captured the image but could not encode it.")

    print(f"AURIX: Image captured and saved as {IMAGE_FILE}")

    return encoded_image.tobytes()


# -----------------------------------
# VISION AI
# -----------------------------------

def analyze_image(image_bytes):

    vision_prompt = """
You are the vision system for AURIX, a future physical AI robot.

Describe what is actually visible in the image.

Rules:
- Be concise.
- Describe observable facts first.
- Do not invent objects that are not visible.
- Do not identify a person's identity.
- Do not claim to know how a person feels.
- If something is uncertain, say it appears to be or may be.
- Mention the most important objects and surroundings.
- Respond naturally as AURIX.

Example style:
"I can see a laptop on a desk, a chair behind it, and several objects
near the monitor."
"""

    last_error = None

    for model in VISION_MODELS:

        try:
            print(f"AURIX: analyzing vision with {model}...")

            response = client.models.generate_content(
                model=model,
                contents=[
                    vision_prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    )
                ]
            )

            if response.text:
                return response.text.strip()

        except Exception as e:
            last_error = e
            print(f"AURIX: {model} failed. Trying backup model...")
            time.sleep(2)

    return f"I could not analyze the image. Error: {last_error}"


# -----------------------------------
# MAIN TEST
# -----------------------------------

print("=" * 55)
print("AURIX VISION v1.0")
print("=" * 55)

try:

    image_bytes = capture_image()

    print("\nAURIX: Thinking about what I see...")

    result = analyze_image(image_bytes)

    print("\nAURIX SEES:")
    print("-" * 55)
    print(result)
    print("-" * 55)

    speak(result)

except Exception as e:

    error_message = f"Vision error: {e}"

    print(error_message)

    speak("I could not use my vision system.")
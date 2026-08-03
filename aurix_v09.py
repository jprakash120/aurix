import os
import time
import re
import wave
import pathlib
import winsound
import subprocess
import webbrowser
from datetime import datetime

import sounddevice as sd
import win32com.client
from google import genai
from google.genai import types


# -----------------------------
# AURIX CONFIGURATION
# -----------------------------

MEMORY_FILE = "aurix_memory.txt"
AUDIO_FILE = "aurix_input.wav"

TEXT_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

AUDIO_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

AURIX_SYSTEM_PROMPT = """
You are AURIX, a fast real-time AI assistant being built first on a laptop and later as hardware.

Identity:
- Your name is AURIX.
- You are a laptop-first AI assistant prototype.
- You are being built to later move into hardware.

Reply style:
- Fast, clear, confident, and practical.
- Reply like an intelligent robot assistant, not a normal chatbot.
- For simple questions, answer shortly.
- For technical questions, explain clearly.
- Help the user build AURIX step by step like a technical partner.
- Keep replies short unless the user asks for details.
- Remember important information from previous conversations when memory is provided.

Important:
- Local laptop commands are handled before reaching the AI model.
- If the user asks about current time, date, opening apps, opening folders, opening websites, creating folders, or listing files, those should be handled locally.
"""


# -----------------------------
# API KEY CHECK
# -----------------------------

if not os.getenv("GEMINI_API_KEY"):
    print("ERROR: GEMINI_API_KEY is missing.")
    print("Set it using this PowerShell command:")
    print('setx GEMINI_API_KEY "your_key_here"')
    print("After setting the key, close PowerShell and open it again.")
    exit()

client = genai.Client()


# -----------------------------
# WINDOWS VOICE SETUP
# -----------------------------

voice_enabled = True

try:
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    speaker.Rate = 0       # -10 slow, 0 normal, 10 fast
    speaker.Volume = 100   # 0 to 100
except Exception as e:
    voice_enabled = False
    print("Voice setup failed.")
    print(e)


def clean_for_speech(text):
    text = re.sub(r"[*#`_>\[\]{}]", "", text)
    text = text.replace("\n", " ")
    return text.strip()


def speak(text):
    if not voice_enabled:
        return

    try:
        clean_text = clean_for_speech(text)
        speaker.Speak(clean_text)
    except Exception as e:
        print("Voice error:")
        print(e)


# -----------------------------
# MEMORY FUNCTIONS
# -----------------------------

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return file.read()
    return ""


def save_memory(user_input, aurix_reply):
    with open(MEMORY_FILE, "a", encoding="utf-8") as file:
        file.write(f"You: {user_input}\n")
        file.write(f"AURIX: {aurix_reply}\n\n")


memory = load_memory()


# -----------------------------
# MICROPHONE RECORDING
# -----------------------------

def record_audio(filename=AUDIO_FILE, duration=5, sample_rate=16000, announce=True):
    print(f"\nAURIX: Listening for {duration} seconds...")

    if announce:
        speak("Listening.")

    try:
        winsound.Beep(900, 250)
    except Exception:
        pass

    audio_data = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16"
    )

    sd.wait()

    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    print("AURIX: Audio captured.")
    return filename


def transcribe_audio(filename=AUDIO_FILE):
    audio_path = pathlib.Path(filename)

    if not audio_path.exists():
        return "Audio file was not created."

    prompt = """
Transcribe the user's speech exactly.
The user may speak English with an Indian accent.
Prefer English words when the audio sounds like English.
Do not translate English into another language.
Return only the spoken words.
Do not explain.
"""

    last_error = None

    for model in AUDIO_MODELS:
        try:
            print(f"AURIX: transcribing with {model}...")

            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(
                        data=audio_path.read_bytes(),
                        mime_type="audio/wav"
                    ),
                    prompt
                ]
            )

            transcript = response.text.strip() if response.text else ""
            return transcript if transcript else "I could not understand the audio."

        except Exception as e:
            print(f"AURIX: {model} transcription failed. Trying backup...")
            last_error = e
            time.sleep(2)

    return f"Audio transcription error: {last_error}"


# -----------------------------
# GEMINI TEXT RESPONSE
# -----------------------------

def ask_gemini(user_input):
    global memory

    recent_memory = memory[-4000:]

    prompt = f"""
{AURIX_SYSTEM_PROMPT}

Previous memory:
{recent_memory}

Current user question:
{user_input}

AURIX:
"""

    last_error = None

    for model in TEXT_MODELS:
        try:
            print(f"AURIX: using {model}...")

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            reply = response.text if response.text else "I received no text response. Try again."
            return reply

        except Exception as e:
            print(f"AURIX: {model} failed. Trying backup model...")
            last_error = e
            time.sleep(2)

    return f"Error: {last_error}"


# -----------------------------
# SMART LOCAL LAPTOP COMMANDS
# -----------------------------

def say_and_print(reply):
    print(f"\nAURIX: {reply}\n")
    speak(reply)


def normalize_command(text):
    text = text.lower().strip()

    # Removes wake-style prefix like "hey aurix open calculator"
    text = re.sub(r"^\s*(hey\s+)?aurix[, ]*", "", text)

    replacements = {
        r"\bwhat's\b": "what is",
        r"\bwhats\b": "what is",
        r"\bwat\b": "what",
        r"\bpls\b": "please",
        r"\bplz\b": "please",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_any(text, words):
    return any(word in text for word in words)


def open_folder(path, folder_name):
    if os.path.exists(path):
        os.startfile(path)
        say_and_print(f"Opening {folder_name}.")
    else:
        say_and_print(f"I could not find the {folder_name} folder.")


def extract_folder_name(command):
    patterns = [
        "create folder called ",
        "create a folder called ",
        "make folder called ",
        "make a folder called ",
        "create folder ",
        "make folder ",
    ]

    for pattern in patterns:
        if pattern in command:
            return command.split(pattern, 1)[1].strip()

    return ""


def handle_local_command(user_input):
    global memory

    command = normalize_command(user_input)
    home = os.path.expanduser("~")

    # Help command
    if command in ["help", "commands", "show commands", "what can you do"]:
        print("""
AURIX COMMANDS:

Voice:
- listen
- auto listen
- wake listen
- voice test

Laptop:
- open notepad
- open calculator
- open chrome
- open youtube
- open gmail
- open documents
- open downloads
- open desktop

Time:
- what time is it
- what is today's date

Files:
- create a folder called project notes
- list files
- read file aurix_memory.txt
- summarize file aurix_memory.txt

Memory:
- show memory
- clear memory

Exit:
- exit
""")
        speak("Command list displayed.")
        return True

    # Voice test
    if command in ["voice test", "test voice", "speak test"] or (
        "voice" in command and "test" in command
    ):
        say_and_print("Aurix voice test is working. I can speak now.")
        return True

    # Memory commands
    if command in ["memory", "show memory"] or (
        "show" in command and "memory" in command
    ):
        print("\nAURIX MEMORY:")
        print(memory[-3000:] if memory else "No memory saved yet.")
        print()
        speak("Memory displayed.")
        return True

    if command in ["clear memory", "delete memory"] or (
        has_any(command, ["clear", "delete", "remove"]) and "memory" in command
    ):
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)
        memory = ""
        say_and_print("Memory cleared.")
        return True

    # Time
    if "time" in command and has_any(command, ["what", "tell", "current", "now", "is it"]):
        now = datetime.now().strftime("%I:%M %p")
        say_and_print(f"The current time is {now}.")
        return True

    # Date
    if "date" in command or "today" in command:
        if has_any(command, ["what", "tell", "current", "today"]):
            today = datetime.now().strftime("%A, %B %d, %Y")
            say_and_print(f"Today is {today}.")
            return True

    # Open apps
    open_intent = has_any(command, ["open", "start", "launch", "run"])

    if open_intent and "notepad" in command:
        subprocess.Popen(["notepad.exe"])
        say_and_print("Opening Notepad.")
        return True

    if open_intent and has_any(command, ["calculator", "calc"]):
        subprocess.Popen(["calc.exe"])
        say_and_print("Opening Calculator.")
        return True

    if open_intent and has_any(command, ["command prompt", "cmd"]):
        subprocess.Popen(["cmd.exe"])
        say_and_print("Opening Command Prompt.")
        return True

    # Open websites
    if open_intent and "google" in command:
        webbrowser.open("https://www.google.com")
        say_and_print("Opening Google.")
        return True

    if open_intent and "youtube" in command:
        webbrowser.open("https://www.youtube.com")
        say_and_print("Opening YouTube.")
        return True

    if open_intent and "gmail" in command:
        webbrowser.open("https://mail.google.com")
        say_and_print("Opening Gmail.")
        return True

    if open_intent and "chrome" in command:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]

        opened = False

        for path in chrome_paths:
            if os.path.exists(path):
                subprocess.Popen([path])
                opened = True
                break

        if not opened:
            webbrowser.open("https://www.google.com")

        say_and_print("Opening Chrome.")
        return True

    # Open folders
    if open_intent and "documents" in command:
        open_folder(os.path.join(home, "Documents"), "Documents")
        return True

    if open_intent and "downloads" in command:
        open_folder(os.path.join(home, "Downloads"), "Downloads")
        return True

    if open_intent and "desktop" in command:
        open_folder(os.path.join(home, "Desktop"), "Desktop")
        return True

    # Read a local file
    if command.startswith("read file "):
        file_name = command.replace("read file ", "").strip()

        if not file_name:
            say_and_print("Please provide a file name.")
            return True

        file_path = os.path.join(os.getcwd(), file_name)

        if not os.path.exists(file_path):
            say_and_print(f"I could not find the file {file_name}.")
            return True

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            print(f"\nAURIX FILE CONTENT: {file_name}")
            print("-" * 50)
            print(content[:3000])
            print("-" * 50)

            speak(f"I opened and displayed {file_name}.")
            return True

        except Exception as e:
            say_and_print(f"I could not read the file. Error: {e}")
            return True

    # Summarize a local file
    if command.startswith("summarize file "):
        file_name = command.replace("summarize file ", "").strip()

        if not file_name:
            say_and_print("Please provide a file name.")
            return True

        file_path = os.path.join(os.getcwd(), file_name)

        if not os.path.exists(file_path):
            say_and_print(f"I could not find the file {file_name}.")
            return True

        allowed_extensions = [".txt", ".py", ".md", ".csv", ".json", ".log"]
        extension = os.path.splitext(file_name)[1].lower()

        if extension not in allowed_extensions:
            say_and_print("For now, I can summarize text-based files like txt, py, md, csv, json, and log files.")
            return True

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            if len(content) > 8000:
                content = content[:8000]

            summary_prompt = f"""
Summarize this file clearly for the user.

File name: {file_name}

File content:
{content}

Give:
1. Simple overview
2. Important points
3. What this file is used for
"""

            summary = ask_gemini(summary_prompt)

            print(f"\nAURIX FILE SUMMARY: {file_name}")
            print("-" * 50)
            print(summary)
            print("-" * 50)

            speak(summary)
            return True

        except Exception as e:
            say_and_print(f"I could not summarize the file. Error: {e}")
            return True

    # List current project files
    if ("list" in command or "show" in command) and "files" in command:
        files = os.listdir(os.getcwd())
        print("\nAURIX FILES:")
        for file in files:
            print("-", file)
        print()
        speak("Files displayed.")
        return True

    # Create folder
    if "folder" in command and has_any(command, ["create", "make"]):
        folder_name = extract_folder_name(command)

        if not folder_name:
            say_and_print("Please provide a folder name.")
            return True

        safe_folder_name = re.sub(r'[<>:"/\\|?*]', "", folder_name)

        if not safe_folder_name:
            say_and_print("That folder name is not valid.")
            return True

        folder_path = os.path.join(os.getcwd(), safe_folder_name)
        os.makedirs(folder_path, exist_ok=True)

        say_and_print(f"Folder created: {safe_folder_name}.")
        return True

    return False


# -----------------------------
# PROCESS USER INPUT
# -----------------------------

def process_user_input(user_input):
    global memory

    command = normalize_command(user_input)

    if command in ["exit", "quit", "stop", "shutdown", "shut down"]:
        print("AURIX: Shutting down.")
        speak("Shutting down.")
        return "shutdown"

    # First check local laptop commands
    if handle_local_command(user_input):
        return "continue"

    # If not a local command, ask AI
    print("AURIX: thinking...")

    aurix_reply = ask_gemini(user_input)

    print(f"\nAURIX: {aurix_reply}\n")

    speak(aurix_reply)

    save_memory(user_input, aurix_reply)
    memory += f"You: {user_input}\nAURIX: {aurix_reply}\n\n"

    return "continue"


# -----------------------------
# ONE-TIME AUTO LISTENING MODE
# -----------------------------

def auto_listen_once():
    print("\nAURIX: Auto listening started.")
    print("AURIX will listen once, respond, then stop listening automatically.\n")

    record_audio(duration=5, announce=True)
    user_input = transcribe_audio()

    print(f"\nYou said: {user_input}\n")

    if not user_input or "error" in user_input.lower():
        speak("I could not understand that.")
        print("AURIX: Auto listening stopped. Back to typing mode.\n")
        return "continue"

    result = process_user_input(user_input)

    print("AURIX: Auto listening stopped. Back to typing mode.\n")

    return result


# -----------------------------
# WAKE PHRASE LISTENING MODE
# -----------------------------

def wake_listen_once():
    print("\nAURIX: Wake phrase mode started.")
    print("Say something like: Hey Aurix open YouTube\n")

    record_audio(duration=5, announce=True)
    user_input = transcribe_audio()

    print(f"\nYou said: {user_input}\n")

    if not user_input or "error" in user_input.lower():
        speak("I could not understand that.")
        print("AURIX: Wake phrase mode stopped.\n")
        return "continue"

    raw_command = user_input.lower().strip()
    normalized = normalize_command(user_input)

    wake_patterns = [
        "hey aurix",
        "aurix",
        "hey oryx",
        "oryx",
        "hey auri x",
    ]

    detected = False
    command_after_wake = ""

    for wake_word in wake_patterns:
        if wake_word in raw_command:
            detected = True
            command_after_wake = raw_command.replace(wake_word, "", 1).strip()
            break

    # If normalize_command removed Aurix from the beginning, accept it as wake phrase.
    if not detected and normalized != raw_command:
        detected = True
        command_after_wake = normalized

    if not detected:
        say_and_print("Wake phrase not detected. Please say Hey Aurix before the command.")
        return "continue"

    if not command_after_wake:
        say_and_print("Yes, I am listening. Please give me a command.")
        return "continue"

    print(f"AURIX detected command: {command_after_wake}")

    result = process_user_input(command_after_wake)

    print("AURIX: Wake phrase mode stopped. Back to typing mode.\n")

    return result


# -----------------------------
# STARTUP
# -----------------------------

print("AURIX v0.9 is online.")
print("Text brain + memory + voice + microphone + laptop commands + one-time auto listen + wake phrase are active.")
print()
print("Commands you can try:")
print("- help")
print("- listen")
print("- auto listen")
print("- wake listen")
print("- wat time is it")
print("- can you open calculator")
print("- launch youtube")
print("- create a folder called project notes")
print("- list files")
print("- read file aurix_memory.txt")
print("- summarize file aurix_memory.txt")
print("- show memory")
print("- clear memory")
print("- voice test")
print("- exit")
print()
print("Note: 'auto listen' listens once, answers, then stops automatically.")
print("Note: 'wake listen' listens once and expects a phrase like 'Hey Aurix open YouTube'.")
print()

speak("Aurix version zero point nine is online. File reading and summarizing are available.")


# -----------------------------
# MAIN LOOP
# -----------------------------

while True:
    raw_input_text = input("You: ").strip()
    command = normalize_command(raw_input_text)

    if not raw_input_text:
        continue

    if command in ["auto listen", "continuous listening", "conversation mode", "voice mode"]:
        result = auto_listen_once()

        if result == "shutdown":
            break

        continue

    if command in ["wake listen", "hey aurix", "wake mode"]:
        result = wake_listen_once()

        if result == "shutdown":
            break

        continue

    if command in ["listen", "mic", "microphone", "voice input"]:
        record_audio(duration=5, announce=True)
        user_input = transcribe_audio()

        print(f"\nYou said: {user_input}\n")

        if not user_input or "error" in user_input.lower():
            print(f"AURIX: {user_input}\n")
            speak("I could not understand the microphone input.")
            continue

        result = process_user_input(user_input)

        if result == "shutdown":
            break

        continue

    result = process_user_input(raw_input_text)

    if result == "shutdown":
        break

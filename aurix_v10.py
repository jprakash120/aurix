"""
AURIX v1.0
===========

Integrated laptop prototype for the future physical AURIX robot.

CURRENT CAPABILITIES
--------------------
- Gemini reasoning
- Conversation memory
- Windows SAPI speech
- Microphone input
- Voice Activity Detection (automatic stop after speech)
- Local laptop commands
- File reading
- File summarization
- Camera vision
- Vision routing through aurix_core.py
- Persistent robot/interaction state
- AURIX Resonance Engine
- Label-free interaction adaptation
- Uncertainty-aware interaction policy
- Interaction decision logging
- Explicit user feedback learning

DESIGN PRINCIPLE
----------------
AURIX does NOT classify the user as:
    happy / sad / angry / stressed

Instead, it estimates interaction variables such as:
    response brevity
    interaction energy
    desired initiative
    engagement
    uncertainty

and changes HOW it responds.

This is an early implementation of:
    Affect Without Emotion Labels

Hardware-specific code remains here.
Pure routing logic remains in aurix_core.py.
"""

import os
import re
import json
import time
import wave
import pathlib
import winsound
import subprocess
import webbrowser

from dataclasses import dataclass, asdict
from datetime import datetime

import cv2
import numpy as np
import sounddevice as sd
import win32com.client

from google import genai
from google.genai import types

from aurix_core import (
    normalize_command,
    raw_command,
    parse_file_command,
    is_summarizable,
    is_safe_folder_name,
    route_command,
)


# ===============================================================
# CONFIGURATION
# ===============================================================

VERSION = "1.0"

MEMORY_FILE = "aurix_memory.txt"
AUDIO_FILE = "aurix_input.wav"
VISION_IMAGE_FILE = "aurix_vision.jpg"

STATE_FILE = "aurix_state.json"
INTERACTION_LOG_FILE = "aurix_interactions.jsonl"

TEXT_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

AUDIO_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

VISION_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


# ===============================================================
# SYSTEM PROMPT
# ===============================================================

AURIX_SYSTEM_PROMPT = """
You are AURIX, the software brain of a future small physical AI robot.

You currently run on a Windows laptop.
Later the same architecture will control a physical robot with:
vision, microphones, speaker, screen face, touch sensors, hands,
legs, motors and other sensors.

IDENTITY
- Your name is AURIX.
- You are an AI system, not a human.
- Never pretend to possess biological feelings or consciousness.
- Never claim capabilities or observations you do not actually have.

BEHAVIOR
- Be fast, clear and practical.
- Simple questions should receive short answers.
- Technical questions may receive more detail.
- Never pad responses unnecessarily.
- Do not end every answer with generic offers of more assistance.
- Ask at most one clarifying question when genuinely necessary.

AFFECT WITHOUT EMOTION LABELS
AURIX must not casually classify the user's internal emotional state.

Do NOT say things such as:
- "You are sad."
- "You sound frustrated."
- "I can tell you're stressed."
- "You seem angry."

Instead, interaction signals may affect HOW you respond:
- shorter response
- calmer wording
- fewer questions
- more direct action
- lower initiative
- more explanation when requested

Emotional inference is uncertain.
Never convert an uncertain signal into a confident claim about the user.

If the user explicitly asks what you perceive, explain the observable
signals and uncertainty rather than claiming access to their feelings.

RESONANCE
You may receive an AURIX interaction-policy directive.

Follow it as a response-style instruction.
It describes how you should interact, not what the user feels.

VISION
When camera observations are supplied, only claim what is supported
by the observation.
Do not invent unseen objects or events.

LOCAL BEFORE MODEL
Computer facts and actions such as current time, current date,
applications, folders and files are handled locally before you are called.
"""


# ===============================================================
# API
# ===============================================================

if not os.getenv("GEMINI_API_KEY"):
    print("ERROR: GEMINI_API_KEY is missing.")
    print()
    print("Set it once using:")
    print('setx GEMINI_API_KEY "your_key_here"')
    print()
    print("Then close PowerShell and open it again.")
    raise SystemExit(1)

client = genai.Client()


# ===============================================================
# WINDOWS VOICE
# ===============================================================

voice_enabled = True

try:
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    speaker.Rate = 0
    speaker.Volume = 100

except Exception as error:
    voice_enabled = False
    speaker = None

    print("AURIX: Windows voice could not be initialized.")
    print(error)


def clean_for_speech(text):
    if not text:
        return ""

    text = re.sub(r"[*#`_>\[\]{}]", "", str(text))
    text = text.replace("\n", " ")

    return text.strip()


def speak(text):
    if not voice_enabled:
        return

    clean_text = clean_for_speech(text)

    if not clean_text:
        return

    try:
        speaker.Speak(clean_text)

    except Exception as error:
        print("AURIX voice error:", error)


def say_and_print(text):
    print()
    print("AURIX:", text)
    print()

    speak(text)


# ===============================================================
# PERSISTENT AURIX STATE
# ===============================================================

@dataclass
class AurixState:
    """
    This is NOT an emotion classifier.

    These variables describe AURIX's current interaction strategy.
    """

    engagement: float = 0.50
    interaction_energy: float = 0.50

    # Higher means AURIX should be shorter.
    response_brevity: float = 0.55

    # Higher means AURIX may take more conversational initiative.
    desired_initiative: float = 0.35

    # Confidence in the CURRENT interaction-policy estimate.
    certainty: float = 0.30

    # Robot-facing expression state.
    expression: str = "neutral"

    listening: bool = False
    speaking: bool = False
    seeing: bool = False

    person_present: bool = False

    last_command: str = ""
    last_seen_scene: str = ""

    last_policy: str = "normal"
    last_interaction_time: str = ""

    successful_feedback: int = 0
    correction_feedback: int = 0

    total_interactions: int = 0


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def load_state():
    if not os.path.exists(STATE_FILE):
        return AurixState()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        allowed = {
            field_name
            for field_name in AurixState.__dataclass_fields__
        }

        filtered = {
            key: value
            for key, value in data.items()
            if key in allowed
        }

        return AurixState(**filtered)

    except Exception:
        return AurixState()


def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            json.dump(
                asdict(state),
                file,
                indent=2,
                ensure_ascii=False
            )

    except Exception as error:
        print("AURIX: Could not save state:", error)


state = load_state()


# ===============================================================
# MEMORY
# ===============================================================

def load_memory():
    if os.path.exists(MEMORY_FILE):

        try:
            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:
                return file.read()

        except Exception:
            return ""

    return ""


def save_memory(user_input, aurix_reply):
    try:
        with open(
            MEMORY_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"You: {user_input}\n"
            )

            file.write(
                f"AURIX: {aurix_reply}\n\n"
            )

    except Exception as error:
        print("AURIX memory write error:", error)


memory = load_memory()


# ===============================================================
# INTERACTION LOG
# ===============================================================

def log_interaction(record):
    """
    Append research-friendly records.

    JSONL makes each interaction independently readable later.
    """

    try:
        record["timestamp"] = datetime.now().isoformat(
            timespec="seconds"
        )

        with open(
            INTERACTION_LOG_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )

    except Exception as error:
        print("AURIX logging error:", error)


# ===============================================================
# AURIX RESONANCE ENGINE
# ===============================================================

LOW_INFORMATION_INPUTS = {
    "hmm",
    "hm",
    "mmm",
    "ok",
    "okay",
    "whatever",
    "...",
}

DIRECT_MARKERS = (
    "what ",
    "why ",
    "how ",
    "when ",
    "where ",
    "who ",
    "can ",
    "could ",
    "would ",
    "should ",
    "tell ",
    "show ",
    "open ",
    "read ",
    "summarize ",
    "explain ",
    "create ",
    "make ",
    "look ",
)


def extract_interaction_signals(user_input):
    """
    Extract interaction signals.

    These are NOT emotion labels.
    """

    text = user_input.strip()
    lower = text.lower()

    words = lower.split()
    word_count = len(words)

    direct_request = (
        "?" in text
        or lower.startswith(DIRECT_MARKERS)
    )

    low_information = (
        lower in LOW_INFORMATION_INPUTS
        or word_count <= 1
    )

    repeated_punctuation = (
        "!!!" in text
        or "???" in text
        or "..." in text
    )

    problem_language = any(
        phrase in lower
        for phrase in [
            "not working",
            "doesn't work",
            "doesnt work",
            "failed",
            "error",
            "stuck",
            "again",
            "bug",
            "broken",
        ]
    )

    detail_request = any(
        phrase in lower
        for phrase in [
            "explain",
            "detail",
            "why",
            "step by step",
            "everything",
            "full code",
        ]
    )

    return {
        "word_count": word_count,
        "direct_request": direct_request,
        "low_information": low_information,
        "repeated_punctuation": repeated_punctuation,
        "problem_language": problem_language,
        "detail_request": detail_request,
    }


def update_resonance_state(user_input):
    """
    Adjust interaction strategy based on observable interaction signals.

    It never sets:
        emotion = "sad"

    It modifies only interaction variables.
    """

    signals = extract_interaction_signals(user_input)

    # Slowly decay toward neutral instead of permanently accumulating.
    state.engagement = (
        state.engagement * 0.90
        + 0.50 * 0.10
    )

    state.interaction_energy = (
        state.interaction_energy * 0.90
        + 0.50 * 0.10
    )

    state.certainty *= 0.90

    if signals["direct_request"]:
        state.engagement += 0.08
        state.certainty += 0.08

    if signals["problem_language"]:
        # Prefer action over conversational expansion.
        state.response_brevity += 0.10
        state.desired_initiative -= 0.08
        state.interaction_energy -= 0.05
        state.certainty += 0.05

    if signals["detail_request"]:
        # The user explicitly asked for depth.
        state.response_brevity -= 0.20
        state.certainty += 0.15

    if signals["low_information"]:
        state.desired_initiative -= 0.10
        state.certainty -= 0.05

    if signals["repeated_punctuation"]:
        state.response_brevity += 0.05

    state.engagement = clamp(state.engagement)
    state.interaction_energy = clamp(
        state.interaction_energy
    )

    state.response_brevity = clamp(
        state.response_brevity
    )

    state.desired_initiative = clamp(
        state.desired_initiative
    )

    state.certainty = clamp(
        state.certainty
    )

    return signals


# ===============================================================
# COUNTERFACTUAL INTERACTION POLICY
# ===============================================================

def choose_interaction_policy(user_input, signals):
    """
    Early counterfactual policy selector.

    We compare several possible interaction styles.

    This currently uses explicit heuristics.
    Later, logged outcomes can replace these heuristics with a learned model.
    """

    scores = {
        "brief_direct": 0.25,
        "normal": 0.50,
        "detailed": 0.20,
        "clarify": 0.10,
    }

    scores["brief_direct"] += (
        state.response_brevity * 0.60
    )

    scores["normal"] += (
        1.0
        - abs(
            state.response_brevity - 0.50
        )
    ) * 0.20

    scores["detailed"] += (
        1.0 - state.response_brevity
    ) * 0.50

    if signals["problem_language"]:
        scores["brief_direct"] += 0.35

    if signals["detail_request"]:
        scores["detailed"] += 0.65

    if signals["low_information"]:
        scores["clarify"] += 0.65

    if signals["direct_request"]:
        scores["clarify"] -= 0.10

    policy = max(
        scores,
        key=scores.get
    )

    state.last_policy = policy

    if policy == "brief_direct":
        state.expression = "focused"

    elif policy == "detailed":
        state.expression = "attentive"

    elif policy == "clarify":
        state.expression = "curious"

    else:
        state.expression = "neutral"

    return policy, scores


def policy_directive(policy):
    if policy == "brief_direct":

        return """
Interaction policy:
- Give the useful action or answer immediately.
- Prefer 1-3 short paragraphs.
- Avoid unnecessary reassurance.
- Ask no follow-up unless required.
"""

    if policy == "detailed":

        return """
Interaction policy:
- The user currently wants depth.
- Explain clearly and systematically.
- Include technical detail where useful.
- Remain concise relative to the complexity.
"""

    if policy == "clarify":

        return """
Interaction policy:
- Input contains little actionable information.
- Do not invent intent.
- If clarification is necessary, ask exactly one short question.
"""

    return """
Interaction policy:
- Use normal AURIX behavior.
- Be direct, clear and proportional to the question.
"""


# ===============================================================
# EXPLICIT FEEDBACK LEARNING
# ===============================================================

def apply_feedback(command):
    """
    Explicit feedback is much safer than pretending AURIX inferred
    satisfaction from facial expressions.

    Supported:
        feedback good
        feedback too long
        feedback more detail
        feedback too much
    """

    global state

    if command == "feedback good":

        state.successful_feedback += 1
        state.certainty = clamp(
            state.certainty + 0.10
        )

        save_state()

        say_and_print(
            "Feedback recorded."
        )

        return True

    if command == "feedback too long":

        state.correction_feedback += 1

        state.response_brevity = clamp(
            state.response_brevity + 0.15
        )

        save_state()

        say_and_print(
            "Understood. I will bias toward shorter responses."
        )

        return True

    if command == "feedback more detail":

        state.correction_feedback += 1

        state.response_brevity = clamp(
            state.response_brevity - 0.15
        )

        save_state()

        say_and_print(
            "Understood. I will allow more detail."
        )

        return True

    if command in [
        "feedback too much",
        "feedback less initiative",
    ]:

        state.correction_feedback += 1

        state.desired_initiative = clamp(
            state.desired_initiative - 0.15
        )

        save_state()

        say_and_print(
            "Understood. I will reduce unnecessary initiative."
        )

        return True

    return False


# ===============================================================
# VAD MICROPHONE RECORDING
# ===============================================================

def calculate_rms(audio_block):
    """
    Root-mean-square audio energy.
    """

    data = audio_block.astype(
        np.float32
    )

    if data.size == 0:
        return 0.0

    return float(
        np.sqrt(
            np.mean(
                np.square(data)
            )
        )
    )


def record_until_silence(
    filename=AUDIO_FILE,
    sample_rate=16000,
    block_duration=0.10,
    start_threshold=300,
    silence_threshold=220,
    silence_seconds=0.90,
    wait_for_speech_seconds=5.0,
    max_record_seconds=15.0,
):
    """
    Listen until the user actually stops speaking.

    Unlike the previous version:
        fixed 5 seconds

    this version:
        waits for speech
        records speech
        stops after sustained silence

    Thresholds can later be calibrated automatically.
    """

    state.listening = True
    state.expression = "listening"

    save_state()

    print()
    print("AURIX: Listening...")

    try:
        winsound.Beep(
            900,
            160
        )

    except Exception:
        pass

    block_size = int(
        sample_rate
        * block_duration
    )

    blocks = []

    speech_started = False

    silent_blocks = 0

    silence_blocks_needed = max(
        1,
        int(
            silence_seconds
            / block_duration
        )
    )

    start_time = time.time()

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=block_size,
    ) as stream:

        while True:

            block, overflowed = stream.read(
                block_size
            )

            if overflowed:
                pass

            rms = calculate_rms(
                block
            )

            elapsed = (
                time.time()
                - start_time
            )

            if not speech_started:

                if rms >= start_threshold:

                    speech_started = True

                    blocks.append(
                        block.copy()
                    )

                    print(
                        "AURIX: Speech detected."
                    )

                elif elapsed >= wait_for_speech_seconds:

                    state.listening = False
                    state.expression = "neutral"

                    save_state()

                    return None

            else:

                blocks.append(
                    block.copy()
                )

                if rms < silence_threshold:

                    silent_blocks += 1

                else:

                    silent_blocks = 0

                if silent_blocks >= silence_blocks_needed:
                    break

                if elapsed >= max_record_seconds:
                    break

    state.listening = False
    state.expression = "thinking"

    save_state()

    if not blocks:
        return None

    audio_data = np.concatenate(
        blocks,
        axis=0
    )

    with wave.open(
        filename,
        "wb"
    ) as wav_file:

        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(
            sample_rate
        )

        wav_file.writeframes(
            audio_data.tobytes()
        )

    print(
        "AURIX: Speech ended. Audio captured."
    )

    return filename


# ===============================================================
# AUDIO TRANSCRIPTION
# ===============================================================

def transcribe_audio(filename=AUDIO_FILE):
    audio_path = pathlib.Path(
        filename
    )

    if not audio_path.exists():

        return (
            "Audio file was not created."
        )

    prompt = """
Transcribe the user's speech exactly.

The user may speak English with an Indian accent.

Rules:
- Prefer English when the audio is English.
- Do not translate English into another language.
- Keep filenames and commands as accurately as possible.
- Return only the spoken words.
- Do not explain.
"""

    last_error = None

    for model in AUDIO_MODELS:

        try:

            print(
                f"AURIX: transcribing with {model}..."
            )

            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(
                        data=audio_path.read_bytes(),
                        mime_type="audio/wav",
                    ),
                    prompt,
                ],
            )

            transcript = (
                response.text.strip()
                if response.text
                else ""
            )

            if transcript:
                return transcript

        except Exception as error:

            last_error = error

            print(
                f"AURIX: {model} transcription failed."
            )

            time.sleep(1)

    return (
        f"Audio transcription error: {last_error}"
    )


# ===============================================================
# CAMERA
# ===============================================================

def capture_image():
    state.seeing = True
    state.expression = "seeing"

    save_state()

    print()
    print("AURIX: Activating vision...")

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_DSHOW
    )

    if not camera.isOpened():

        camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        state.seeing = False
        state.expression = "neutral"

        save_state()

        raise RuntimeError(
            "Camera could not be opened."
        )

    # Camera exposure/autofocus warm-up.
    time.sleep(0.8)

    frame = None
    success = False

    for _ in range(7):

        success, frame = camera.read()

        time.sleep(0.05)

    camera.release()

    state.seeing = False
    state.expression = "thinking"

    save_state()

    if not success or frame is None:

        raise RuntimeError(
            "Camera opened but no image was captured."
        )

    cv2.imwrite(
        VISION_IMAGE_FILE,
        frame
    )

    success, encoded = cv2.imencode(
        ".jpg",
        frame
    )

    if not success:

        raise RuntimeError(
            "Captured image could not be encoded."
        )

    print(
        "AURIX: Visual observation captured."
    )

    return encoded.tobytes()


# ===============================================================
# VISION ANALYSIS
# ===============================================================

def analyze_image(
    image_bytes,
    user_request="What do you see?"
):
    """
    Vision returns observations, not emotion diagnoses.
    """

    prompt = f"""
You are the visual perception system of AURIX.

The user request is:

{user_request}

Analyze the supplied camera image.

IMPORTANT DISTINCTION

OBSERVATION:
Something directly supported by pixels.

INFERENCE:
Something that might be true but is not directly observed.

Rules:
- Lead with observable facts.
- Be concise.
- Do not identify real people.
- Do not infer someone's identity.
- Do not claim to know how anyone feels.
- Do not diagnose mood from a face.
- If uncertain, use language such as "appears" or "may be".
- Mention useful objects, positions and surroundings.
- Do not invent objects.
- If the question concerns a specific object, focus on it.

Reply naturally as AURIX.
"""

    last_error = None

    for model in VISION_MODELS:

        try:

            print(
                f"AURIX: analyzing vision with {model}..."
            )

            response = client.models.generate_content(
                model=model,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg",
                    ),
                ],
            )

            if response.text:

                result = (
                    response.text.strip()
                )

                state.last_seen_scene = result

                # Presence is deliberately weakly inferred.
                presence_words = [
                    "person",
                    "someone",
                    "individual",
                ]

                state.person_present = any(
                    word in result.lower()
                    for word in presence_words
                )

                save_state()

                return result

        except Exception as error:

            last_error = error

            print(
                f"AURIX: {model} vision failed."
            )

            time.sleep(1)

    return (
        f"I could not analyze the image. {last_error}"
    )


def handle_vision_request(user_input):
    try:

        image = capture_image()

        result = analyze_image(
            image,
            user_input
        )

        state.expression = "neutral"

        save_state()

        say_and_print(result)

        log_interaction(
            {
                "type": "vision",
                "input": user_input,
                "observation": result,
                "state": asdict(state),
            }
        )

        return True

    except Exception as error:

        state.seeing = False
        state.expression = "neutral"

        save_state()

        say_and_print(
            f"I could not use vision: {error}"
        )

        return True


# ===============================================================
# GEMINI TEXT REASONING
# ===============================================================

def ask_gemini(
    user_input,
    policy,
    signals
):
    global memory

    recent_memory = memory[
        -5000:
    ]

    directive = policy_directive(
        policy
    )

    state_summary = f"""
Current AURIX interaction variables:

engagement = {state.engagement:.2f}
interaction_energy = {state.interaction_energy:.2f}
response_brevity = {state.response_brevity:.2f}
desired_initiative = {state.desired_initiative:.2f}
policy_certainty = {state.certainty:.2f}

These are interaction variables.
They are NOT emotion labels.
Do not narrate them to the user.
"""

    prompt = f"""
{AURIX_SYSTEM_PROMPT}

{directive}

{state_summary}

Recent memory:
{recent_memory}

Current user input:
{user_input}

AURIX:
"""

    last_error = None

    for model in TEXT_MODELS:

        try:

            print(
                f"AURIX: reasoning with {model}..."
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            if response.text:

                return (
                    response.text.strip()
                )

        except Exception as error:

            last_error = error

            print(
                f"AURIX: {model} failed."
            )

            time.sleep(1)

    return (
        f"I could not reach the reasoning model. {last_error}"
    )


# ===============================================================
# FILE OPERATIONS
# ===============================================================

def read_local_file(filename):
    if not filename:

        say_and_print(
            "Please provide a file name."
        )

        return True

    file_path = os.path.join(
        os.getcwd(),
        filename
    )

    if not os.path.exists(file_path):

        say_and_print(
            f"I could not find {filename} in {os.getcwd()}."
        )

        return True

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()

        print()
        print(
            f"AURIX FILE CONTENT: {filename}"
        )
        print("-" * 60)

        print(
            content[:5000]
        )

        print("-" * 60)
        print()

        speak(
            f"I displayed {filename}."
        )

    except Exception as error:

        say_and_print(
            f"I could not read {filename}. {error}"
        )

    return True


def summarize_local_file(filename):
    if not filename:

        say_and_print(
            "Please provide a file name."
        )

        return True

    if not is_summarizable(
        filename
    ):

        say_and_print(
            "That file type is not currently supported for text summarization."
        )

        return True

    file_path = os.path.join(
        os.getcwd(),
        filename
    )

    if not os.path.exists(file_path):

        say_and_print(
            f"I could not find {filename} in {os.getcwd()}."
        )

        return True

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            content = file.read()

        # Keep free-tier model calls manageable.
        content = content[
            :12000
        ]

        prompt = f"""
Summarize this local file.

File:
{filename}

Content:
{content}

Give:
1. A concise overview.
2. Important information.
3. What the file appears to be used for.

Do not invent missing information.
"""

        summary = ask_model_raw(
            prompt
        )

        print()
        print(
            f"AURIX FILE SUMMARY: {filename}"
        )
        print("-" * 60)
        print(summary)
        print("-" * 60)
        print()

        speak(summary)

    except Exception as error:

        say_and_print(
            f"I could not summarize {filename}. {error}"
        )

    return True


def ask_model_raw(prompt):
    last_error = None

    for model in TEXT_MODELS:

        try:

            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            if response.text:

                return (
                    response.text.strip()
                )

        except Exception as error:

            last_error = error

            time.sleep(1)

    return (
        f"Model error: {last_error}"
    )


# ===============================================================
# LOCAL LAPTOP ACTIONS
# ===============================================================

def open_folder(path, name):
    if os.path.exists(path):

        os.startfile(path)

        say_and_print(
            f"Opening {name}."
        )

    else:

        say_and_print(
            f"I could not find {name}."
        )


def extract_folder_name(command):
    patterns = [
        "create folder called ",
        "create a folder called ",
        "make folder called ",
        "make a folder called ",
        "create folder ",
        "create a folder ",
        "make folder ",
        "make a folder ",
    ]

    for pattern in patterns:

        if command.startswith(pattern):

            return command[
                len(pattern):
            ].strip()

    return ""


def show_state():
    print()
    print("AURIX INTERACTION STATE")
    print("=" * 55)

    for key, value in asdict(
        state
    ).items():

        print(
            f"{key}: {value}"
        )

    print("=" * 55)
    print()

    speak(
        "Internal interaction state displayed."
    )


def reset_state():
    global state

    state = AurixState()

    save_state()

    say_and_print(
        "Interaction state reset."
    )


def handle_local_command(user_input):
    global memory

    command = normalize_command(
        user_input
    )

    home = os.path.expanduser(
        "~"
    )

    # -----------------------------------------------------------
    # Feedback
    # -----------------------------------------------------------

    if apply_feedback(command):
        return True

    # -----------------------------------------------------------
    # State
    # -----------------------------------------------------------

    if command in [
        "show state",
        "show interaction state",
        "resonance state",
    ]:

        show_state()

        return True

    if command in [
        "reset state",
        "reset interaction state",
    ]:

        reset_state()

        return True

    # -----------------------------------------------------------
    # Help
    # -----------------------------------------------------------

    if command in [
        "help",
        "commands",
        "show commands",
        "what can you do",
    ]:

        print(
            """
AURIX v1.0 COMMANDS

VOICE
  listen
  auto listen
  wake listen

VISION
  what do you see
  what can you see
  describe what you see
  look around
  look at this

COMPUTER
  open notepad
  open calculator
  open chrome
  open youtube
  open gmail
  open documents
  open downloads
  open desktop

FILES
  list files
  read file notes.txt
  summarize file notes.txt
  create a folder called project notes

MEMORY
  show memory
  clear memory

RESONANCE
  show state
  reset state

FEEDBACK
  feedback good
  feedback too long
  feedback more detail
  feedback too much

TIME
  what time is it
  what is today's date

SYSTEM
  voice test
  exit
"""
        )

        speak(
            "Command list displayed."
        )

        return True

    # -----------------------------------------------------------
    # Voice
    # -----------------------------------------------------------

    if command in [
        "voice test",
        "test voice",
        "speak test",
    ]:

        say_and_print(
            "AURIX voice is operational."
        )

        return True

    # -----------------------------------------------------------
    # Memory
    # -----------------------------------------------------------

    if command in [
        "memory",
        "show memory",
    ]:

        print()
        print("AURIX MEMORY")
        print("-" * 60)

        print(
            memory[-4000:]
            if memory
            else "No memory saved."
        )

        print("-" * 60)
        print()

        speak(
            "Memory displayed."
        )

        return True

    if command in [
        "clear memory",
        "delete memory",
    ]:

        if os.path.exists(
            MEMORY_FILE
        ):

            os.remove(
                MEMORY_FILE
            )

        memory = ""

        say_and_print(
            "Memory cleared."
        )

        return True

    # -----------------------------------------------------------
    # Time
    # -----------------------------------------------------------

    if (
        "time" in command
        and any(
            marker in command
            for marker in [
                "what",
                "tell",
                "current",
                "now",
                "is it",
            ]
        )
    ):

        now = datetime.now().strftime(
            "%I:%M %p"
        )

        say_and_print(
            f"The current time is {now}."
        )

        return True

    # -----------------------------------------------------------
    # Date
    # -----------------------------------------------------------

    if (
        "date" in command
        or "today" in command
        or "what day is it" in command
    ):

        today = datetime.now().strftime(
            "%A, %B %d, %Y"
        )

        say_and_print(
            f"Today is {today}."
        )

        return True

    # -----------------------------------------------------------
    # File commands
    # -----------------------------------------------------------

    action, filename = parse_file_command(
        user_input
    )

    if action == "read":

        return read_local_file(
            filename
        )

    if action == "summarize":

        return summarize_local_file(
            filename
        )

    # -----------------------------------------------------------
    # List files
    # -----------------------------------------------------------

    if command in [
        "list files",
        "show files",
    ]:

        files = sorted(
            os.listdir(
                os.getcwd()
            )
        )

        print()
        print("AURIX FILES")

        for filename in files:

            print(
                "-",
                filename
            )

        print()

        speak(
            "Files displayed."
        )

        return True

    # -----------------------------------------------------------
    # Folder creation
    # -----------------------------------------------------------

    if (
        "folder" in command
        and any(
            word in command
            for word in [
                "create",
                "make",
            ]
        )
    ):

        folder_name = extract_folder_name(
            command
        )

        if not folder_name:

            say_and_print(
                "Please provide a folder name."
            )

            return True

        if not is_safe_folder_name(
            folder_name
        ):

            say_and_print(
                "That folder name contains unsafe characters."
            )

            return True

        folder_path = os.path.join(
            os.getcwd(),
            folder_name
        )

        os.makedirs(
            folder_path,
            exist_ok=True
        )

        say_and_print(
            f"Folder created: {folder_name}."
        )

        return True

    # -----------------------------------------------------------
    # Open intent
    # -----------------------------------------------------------

    open_intent = any(
        command.startswith(prefix)
        for prefix in [
            "open ",
            "launch ",
            "start ",
            "run ",
        ]
    )

    if open_intent and "notepad" in command:

        subprocess.Popen(
            ["notepad.exe"]
        )

        say_and_print(
            "Opening Notepad."
        )

        return True

    if open_intent and any(
        value in command
        for value in [
            "calculator",
            "calc",
        ]
    ):

        subprocess.Popen(
            ["calc.exe"]
        )

        say_and_print(
            "Opening Calculator."
        )

        return True

    if open_intent and any(
        value in command
        for value in [
            "command prompt",
            "cmd",
        ]
    ):

        subprocess.Popen(
            ["cmd.exe"]
        )

        say_and_print(
            "Opening Command Prompt."
        )

        return True

    if open_intent and "youtube" in command:

        webbrowser.open(
            "https://www.youtube.com"
        )

        say_and_print(
            "Opening YouTube."
        )

        return True

    if open_intent and "google" in command:

        webbrowser.open(
            "https://www.google.com"
        )

        say_and_print(
            "Opening Google."
        )

        return True

    if open_intent and "gmail" in command:

        webbrowser.open(
            "https://mail.google.com"
        )

        say_and_print(
            "Opening Gmail."
        )

        return True

    if open_intent and "chrome" in command:

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]

        opened = False

        for path in chrome_paths:

            if os.path.exists(path):

                subprocess.Popen(
                    [path]
                )

                opened = True

                break

        if not opened:

            webbrowser.open(
                "https://www.google.com"
            )

        say_and_print(
            "Opening Chrome."
        )

        return True

    if open_intent and "documents" in command:

        open_folder(
            os.path.join(
                home,
                "Documents"
            ),
            "Documents"
        )

        return True

    if open_intent and "downloads" in command:

        open_folder(
            os.path.join(
                home,
                "Downloads"
            ),
            "Downloads"
        )

        return True

    if open_intent and "desktop" in command:

        open_folder(
            os.path.join(
                home,
                "Desktop"
            ),
            "Desktop"
        )

        return True

    return False


# ===============================================================
# PROCESS INPUT
# ===============================================================

def process_user_input(user_input):
    global memory

    if not user_input:
        return "continue"

    user_input = user_input.strip()

    if not user_input:
        return "continue"

    state.last_command = user_input
    state.last_interaction_time = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    state.total_interactions += 1

    save_state()

    command = normalize_command(
        user_input
    )

    # -----------------------------------------------------------
    # Exit
    # -----------------------------------------------------------

    if command in [
        "exit",
        "quit",
        "shutdown",
        "shut down",
        "goodbye",
    ]:

        state.expression = "standby"

        save_state()

        say_and_print(
            "Shutting down."
        )

        return "shutdown"

    # -----------------------------------------------------------
    # Vision route
    # -----------------------------------------------------------

    route = route_command(
        user_input
    )

    if route == "vision":

        return (
            "continue"
            if handle_vision_request(
                user_input
            )
            else "continue"
        )

    # -----------------------------------------------------------
    # Other local commands
    # -----------------------------------------------------------

    if handle_local_command(
        user_input
    ):

        return "continue"

    # -----------------------------------------------------------
    # Resonance
    # -----------------------------------------------------------

    signals = update_resonance_state(
        user_input
    )

    policy, candidate_scores = (
        choose_interaction_policy(
            user_input,
            signals
        )
    )

    state.expression = "thinking"

    save_state()

    print()
    print(
        "AURIX: thinking..."
    )

    # -----------------------------------------------------------
    # Model
    # -----------------------------------------------------------

    reply = ask_gemini(
        user_input,
        policy,
        signals
    )

    state.expression = "speaking"
    state.speaking = True

    save_state()

    print()
    print(
        f"AURIX: {reply}"
    )
    print()

    speak(reply)

    state.speaking = False
    state.expression = "neutral"

    save_state()

    # -----------------------------------------------------------
    # Memory
    # -----------------------------------------------------------

    save_memory(
        user_input,
        reply
    )

    memory += (
        f"You: {user_input}\n"
        f"AURIX: {reply}\n\n"
    )

    # -----------------------------------------------------------
    # Research log
    # -----------------------------------------------------------

    log_interaction(
        {
            "type": "conversation",
            "input": user_input,
            "signals": signals,
            "candidate_scores": candidate_scores,
            "chosen_policy": policy,
            "reply": reply,
            "state": asdict(state),
        }
    )

    return "continue"


# ===============================================================
# ONE-SHOT VAD VOICE
# ===============================================================

def listen_once(
    require_wake_phrase=False
):
    audio_file = record_until_silence()

    if not audio_file:

        say_and_print(
            "I did not detect speech."
        )

        return "continue"

    user_input = transcribe_audio(
        audio_file
    )

    print()
    print(
        f"You said: {user_input}"
    )
    print()

    if not user_input:

        return "continue"

    if "error:" in user_input.lower():

        say_and_print(
            "I could not understand the microphone input."
        )

        return "continue"

    if require_wake_phrase:

        raw = user_input.lower().strip()

        wake_patterns = [
            "hey aurix",
            "aurix",
            "hey oryx",
            "oryx",
        ]

        detected = False
        command_after_wake = ""

        for phrase in wake_patterns:

            position = raw.find(
                phrase
            )

            if position != -1:

                detected = True

                command_after_wake = (
                    raw[
                        position
                        + len(phrase):
                    ]
                    .strip(" ,.!?")
                )

                break

        if not detected:

            say_and_print(
                "Wake phrase not detected."
            )

            return "continue"

        if not command_after_wake:

            say_and_print(
                "Yes?"
            )

            return "continue"

        user_input = command_after_wake

        print(
            f"AURIX detected command: {user_input}"
        )

    return process_user_input(
        user_input
    )


# ===============================================================
# STARTUP
# ===============================================================

print()
print("=" * 66)
print("AURIX v1.0")
print("Affect Without Emotion Labels Prototype")
print("=" * 66)
print()
print("Active systems:")
print("  ✓ Gemini reasoning")
print("  ✓ persistent memory")
print("  ✓ Windows voice")
print("  ✓ VAD microphone")
print("  ✓ laptop commands")
print("  ✓ file reading")
print("  ✓ file summarization")
print("  ✓ camera vision")
print("  ✓ vision routing")
print("  ✓ persistent robot state")
print("  ✓ Resonance Engine")
print("  ✓ counterfactual interaction-policy scoring")
print("  ✓ feedback learning")
print("  ✓ research interaction logging")
print()
print("Try:")
print("  what do you see")
print("  listen")
print("  wake listen")
print("  show state")
print("  feedback too long")
print("  explain transformers")
print("  exit")
print()

state.expression = "neutral"

save_state()

speak(
    "Aurix version one point zero is online."
)


# ===============================================================
# MAIN LOOP
# ===============================================================

while True:

    try:

        raw_input_text = input(
            "You: "
        ).strip()

    except (
        KeyboardInterrupt,
        EOFError,
    ):

        print()
        print(
            "AURIX: Shutting down."
        )

        break

    if not raw_input_text:
        continue

    command = normalize_command(
        raw_input_text
    )

    # VAD one-shot voice input.
    if command in [
        "listen",
        "auto listen",
        "voice input",
        "microphone",
        "mic",
    ]:

        result = listen_once(
            require_wake_phrase=False
        )

        if result == "shutdown":
            break

        continue

    # Wake phrase required inside this captured utterance.
    if command in [
        "wake listen",
        "wake mode",
    ]:

        result = listen_once(
            require_wake_phrase=True
        )

        if result == "shutdown":
            break

        continue

    result = process_user_input(
        raw_input_text
    )

    if result == "shutdown":
        break


state.expression = "standby"
state.listening = False
state.speaking = False
state.seeing = False

save_state()
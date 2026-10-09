"""
AURIX v1.3
==========

Provider-independent AI
+
Learning Resonance Engine
+
Episodic World Memory

Major changes from v1.0:

1. Groq-first reasoning.
2. Groq Whisper speech recognition.
3. Groq multimodal vision.
4. Gemini optional fallback.
5. LinUCB contextual-bandit interaction policy.
6. Silence is a legitimate interaction action.
7. Explicit feedback trains the policy.
8. SQLite episodic memory.
9. Vision observations persist across sessions.
10. Visual change detection.
11. Local control words no longer reach the LLM.
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

from aurix_ai import AurixAI
from aurix_learning import (
    LinUCBBandit,
    context_vector,
    eligible_actions,
    policy_directive,
    feedback_reward,
)
from aurix_world_memory import (
    EpisodicMemory,
)
from aurix_core import (
    normalize_command,
    parse_file_command,
    is_summarizable,
    is_safe_folder_name,
    route_command,
)


# ===============================================================
# CONFIG
# ===============================================================

VERSION = "1.3"

AUDIO_FILE = "aurix_input.wav"
VISION_IMAGE_FILE = "aurix_vision.jpg"

STATE_FILE = "aurix_state.json"
CHAT_MEMORY_FILE = "aurix_memory.txt"

PENDING_FILE = "aurix_pending.json"

INTERACTION_LOG = (
    "aurix_interactions.jsonl"
)

DEBUG_POLICY = True


# ===============================================================
# AI / MEMORY / LEARNING
# ===============================================================

ai = AurixAI()

bandit = LinUCBBandit(
    path="aurix_bandit.json",
    alpha=0.65,
)

world = EpisodicMemory(
    db_path="aurix_world.db"
)


# ===============================================================
# SYSTEM PROMPT
# ===============================================================

SYSTEM_PROMPT = """
You are AURIX, the software intelligence of a future embodied AI robot.

AURIX currently runs on a Windows laptop.

CORE RULES

1. Local-before-model:
   Do not pretend to perform computer actions that were not performed.

2. Honesty:
   Never invent observations, memory, actions, or capabilities.

3. Affect without emotion labels:
   Do not casually classify the user's internal emotional state.

Do not say:
"You are sad."
"You sound stressed."
"You seem angry."

Instead, interaction signals may change HOW you respond.

4. AURIX does not claim biological feelings or consciousness.

5. If asked directly what you perceive about someone's emotional state,
describe observable evidence and uncertainty.

6. Be concise by default.

7. AURIX has an episodic world-memory system.
Only use memories supplied in the prompt.
Never claim a memory that is not supplied.

8. The interaction policy selected by the Resonance Engine controls
response style. It does not describe the user's feelings.

9. Do not mention internal policy scores unless explicitly asked.
"""


# ===============================================================
# ROBOT STATE
# ===============================================================

@dataclass
class RobotState:

    expression: str = "neutral"

    listening: bool = False
    speaking: bool = False
    seeing: bool = False

    person_present: bool = False

    response_brevity: float = 0.50
    desired_initiative: float = 0.35
    certainty: float = 0.30

    last_command: str = ""
    last_policy: str = "normal"
    last_seen_scene: str = ""

    total_interactions: int = 0

    last_interaction_time: str = ""


def load_state():

    if not os.path.exists(
        STATE_FILE
    ):
        return RobotState()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        valid = {
            name
            for name
            in RobotState.__dataclass_fields__
        }

        filtered = {
            key: value
            for key, value in data.items()
            if key in valid
        }

        return RobotState(
            **filtered
        )

    except Exception:

        return RobotState()


state = load_state()


def save_state():

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            asdict(
                state
            ),
            file,
            indent=2,
        )


# ===============================================================
# WINDOWS SPEECH
# ===============================================================

speaker = None
voice_enabled = True

try:

    speaker = (
        win32com.client.Dispatch(
            "SAPI.SpVoice"
        )
    )

    speaker.Rate = 0
    speaker.Volume = 100

except Exception as error:

    voice_enabled = False

    print(
        "AURIX voice unavailable:",
        error,
    )


def clean_for_speech(text):

    text = str(
        text
        or ""
    )

    text = re.sub(
        r"[*#`_>\[\]{}]",
        "",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def speak(text):

    if (
        not voice_enabled
        or not speaker
    ):
        return

    text = clean_for_speech(
        text
    )

    if text:

        try:
            speaker.Speak(
                text
            )
        except Exception:
            pass


def say_and_print(text):

    print()
    print(
        "AURIX:",
        text,
    )
    print()

    speak(
        text
    )


# ===============================================================
# CHAT MEMORY
# ===============================================================

def load_chat_memory():

    if not os.path.exists(
        CHAT_MEMORY_FILE
    ):
        return ""

    try:

        with open(
            CHAT_MEMORY_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return file.read()

    except Exception:

        return ""


chat_memory = load_chat_memory()


def append_chat_memory(
    user_input,
    reply,
):

    global chat_memory

    entry = (
        f"You: {user_input}\n"
        f"AURIX: {reply}\n\n"
    )

    with open(
        CHAT_MEMORY_FILE,
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            entry
        )

    chat_memory += entry


# ===============================================================
# RESEARCH LOG
# ===============================================================

def log_event(data):

    record = dict(
        data
    )

    record["timestamp"] = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    with open(
        INTERACTION_LOG,
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )


# ===============================================================
# PENDING BANDIT DECISION
# ===============================================================

def save_pending(
    action,
    features,
    user_input,
    reply,
    scores,
):

    payload = {
        "action": action,
        "features": (
            np.asarray(
                features,
                dtype=float,
            ).tolist()
        ),
        "user_input": user_input,
        "reply": reply,
        "scores": scores,
        "timestamp": (
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),
    }

    with open(
        PENDING_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
        )


def load_pending():

    if not os.path.exists(
        PENDING_FILE
    ):
        return None

    try:

        with open(
            PENDING_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(
                file
            )

    except Exception:

        return None


def clear_pending():

    if os.path.exists(
        PENDING_FILE
    ):

        os.remove(
            PENDING_FILE
        )


# ===============================================================
# FEEDBACK LEARNING
# ===============================================================

def handle_feedback(
    command
):

    reward = feedback_reward(
        command
    )

    if reward is None:
        return False

    pending = load_pending()

    if not pending:

        say_and_print(
            "There is no previous learning decision to rate."
        )

        return True

    action = pending.get(
        "action"
    )

    features = np.asarray(
        pending.get(
            "features",
            [],
        ),
        dtype=float,
    )

    if len(
        features
    ) != bandit.dimension:

        say_and_print(
            "The previous learning record is incompatible."
        )

        clear_pending()

        return True

    bandit.update(
        action,
        features,
        reward,
    )

    if command == "feedback too long":

        state.response_brevity = min(
            1.0,
            state.response_brevity
            + 0.10,
        )

    elif command == "feedback more detail":

        state.response_brevity = max(
            0.0,
            state.response_brevity
            - 0.10,
        )

    elif command == "feedback unnecessary":

        state.desired_initiative = max(
            0.0,
            state.desired_initiative
            - 0.10,
        )

    save_state()

    world.add_episode(
        modality="feedback",
        event_type="policy_feedback",
        summary=(
            f"Feedback {command} "
            f"for action {action}."
        ),
        payload={
            "action": action,
            "reward": reward,
        },
        significance=0.8,
    )

    log_event(
        {
            "type": "feedback",
            "feedback": command,
            "action": action,
            "reward": reward,
        }
    )

    clear_pending()

    say_and_print(
        f"Feedback learned. Previous policy: {action}."
    )

    return True


# ===============================================================
# VAD MICROPHONE
# ===============================================================

def rms(
    block
):

    data = block.astype(
        np.float32
    )

    if data.size == 0:
        return 0.0

    return float(
        np.sqrt(
            np.mean(
                np.square(
                    data
                )
            )
        )
    )


def record_until_silence(
    filename=AUDIO_FILE,
    sample_rate=16000,
    block_duration=0.10,
    start_threshold=300,
    silence_threshold=220,
    silence_seconds=0.9,
    wait_seconds=6.0,
    max_seconds=18.0,
):

    state.listening = True
    state.expression = "listening"

    save_state()

    print()
    print(
        "AURIX: Listening..."
    )

    try:
        winsound.Beep(
            900,
            150,
        )
    except Exception:
        pass

    block_size = int(
        sample_rate
        * block_duration
    )

    required_silence = max(
        1,
        int(
            silence_seconds
            / block_duration
        ),
    )

    blocks = []

    speech_started = False
    silent_blocks = 0

    start = time.time()

    try:

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=block_size,
        ) as stream:

            while True:

                block, _ = stream.read(
                    block_size
                )

                energy = rms(
                    block
                )

                elapsed = (
                    time.time()
                    - start
                )

                if not speech_started:

                    if energy >= start_threshold:

                        speech_started = True

                        print(
                            "AURIX: Speech detected."
                        )

                        blocks.append(
                            block.copy()
                        )

                    elif elapsed >= wait_seconds:

                        return None

                else:

                    blocks.append(
                        block.copy()
                    )

                    if energy < silence_threshold:

                        silent_blocks += 1

                    else:

                        silent_blocks = 0

                    if (
                        silent_blocks
                        >= required_silence
                    ):
                        break

                    if elapsed >= max_seconds:
                        break

    finally:

        state.listening = False
        state.expression = "neutral"

        save_state()

    if not blocks:
        return None

    audio = np.concatenate(
        blocks,
        axis=0,
    )

    with wave.open(
        filename,
        "wb",
    ) as wav:

        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(
            sample_rate
        )

        wav.writeframes(
            audio.tobytes()
        )

    print(
        "AURIX: Speech ended."
    )

    return filename


# ===============================================================
# CAMERA
# ===============================================================

def capture_image():

    state.seeing = True
    state.expression = "seeing"

    save_state()

    print()
    print(
        "AURIX: Activating vision..."
    )

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_DSHOW,
    )

    if not camera.isOpened():

        camera.release()

        camera = cv2.VideoCapture(
            0
        )

    if not camera.isOpened():

        state.seeing = False
        state.expression = "neutral"

        save_state()

        raise RuntimeError(
            "Camera could not be opened."
        )

    try:

        time.sleep(
            0.8
        )

        frame = None
        success = False

        for _ in range(
            7
        ):

            success, frame = camera.read()

            time.sleep(
                0.05
            )

    finally:

        camera.release()

    state.seeing = False
    state.expression = "thinking"

    save_state()

    if (
        not success
        or frame is None
    ):

        raise RuntimeError(
            "Camera opened but no usable frame was captured."
        )

    cv2.imwrite(
        VISION_IMAGE_FILE,
        frame,
    )

    encoded_success, encoded = (
        cv2.imencode(
            ".jpg",
            frame,
        )
    )

    if not encoded_success:

        raise RuntimeError(
            "Could not encode camera frame."
        )

    return encoded.tobytes()


# ===============================================================
# VISION
# ===============================================================

def handle_vision(
    user_input
):

    try:

        image_bytes = capture_image()

        prompt = f"""
User asked:
{user_input}

Describe useful observable information in the current camera frame.

If positions are useful, describe them.
Do not identify a real person.
Do not assert someone's emotional state.
"""

        result = ai.analyze_image(
            image_bytes,
            prompt,
        )

        observation = result.text

        state.last_seen_scene = (
            observation
        )

        state.person_present = any(
            word in observation.lower()
            for word in (
                "person",
                "individual",
                "someone",
            )
        )

        state.expression = "neutral"

        save_state()

        memory_result = (
            world.record_vision_observation(
                observation,
                provider=result.provider,
                model=result.model,
            )
        )

        say_and_print(
            observation
        )

        if (
            DEBUG_POLICY
            and memory_result[
                "changed"
            ]
        ):

            print(
                "AURIX MEMORY: meaningful visual change recorded."
            )

            print(
                "Novelty:",
                memory_result[
                    "novelty"
                ],
            )

        log_event(
            {
                "type": "vision",
                "input": user_input,
                "observation": observation,
                "provider": result.provider,
                "model": result.model,
                "novelty": memory_result[
                    "novelty"
                ],
                "changed": memory_result[
                    "changed"
                ],
            }
        )

    except Exception as error:

        state.seeing = False
        state.expression = "neutral"

        save_state()

        say_and_print(
            f"Vision failed: {error}"
        )

    return True


# ===============================================================
# WORLD MEMORY COMMANDS
# ===============================================================

def show_recent_memories():

    episodes = world.recent(
        limit=10
    )

    print()
    print(
        "AURIX EPISODIC MEMORY"
    )
    print(
        "=" * 65
    )

    if not episodes:

        print(
            "No episodes recorded."
        )

    else:

        for episode in reversed(
            episodes
        ):

            print(
                world.format_episode(
                    episode
                )
            )

    print(
        "=" * 65
    )
    print()

    speak(
        "Recent episodic memories displayed."
    )


def recall_previous_vision():

    episodes = world.recent(
        limit=3,
        modality="vision",
        event_type="vision_observation",
    )

    if not episodes:

        say_and_print(
            "I do not have an earlier visual observation yet."
        )

        return

    if len(
        episodes
    ) >= 2:

        episode = episodes[1]

    else:

        episode = episodes[0]

    say_and_print(
        "Earlier I recorded: "
        + episode["summary"]
    )


def recall_latest_change():

    change = world.latest(
        event_type="scene_change"
    )

    if not change:

        say_and_print(
            "I have not recorded a significant scene change yet."
        )

        return

    try:

        payload = json.loads(
            change["payload"]
        )

    except Exception:

        payload = {}

    current = payload.get(
        "current"
    )

    previous = payload.get(
        "previous"
    )

    novelty = payload.get(
        "novelty"
    )

    print()
    print(
        "AURIX LATEST VISUAL CHANGE"
    )
    print(
        "-" * 65
    )
    print(
        "Previous:",
        previous,
    )
    print()
    print(
        "Current:",
        current,
    )
    print()
    print(
        "Novelty:",
        novelty,
    )
    print(
        "-" * 65
    )
    print()

    speak(
        "I displayed the latest visual scene change."
    )


# ===============================================================
# FILE HELPERS
# ===============================================================

def read_file(
    filename
):

    if not filename:

        say_and_print(
            "Please provide a filename."
        )

        return True

    path = os.path.join(
        os.getcwd(),
        filename,
    )

    if not os.path.isfile(
        path
    ):

        say_and_print(
            f"I could not find {filename}."
        )

        return True

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            content = file.read()

        print()
        print(
            f"FILE: {filename}"
        )
        print(
            "-" * 65
        )
        print(
            content[:10000]
        )
        print(
            "-" * 65
        )
        print()

        world.add_episode(
            modality="computer",
            event_type="file_read",
            summary=(
                f"Read local file {filename}."
            ),
            payload={
                "filename": filename
            },
            significance=0.4,
        )

        speak(
            f"I displayed {filename}."
        )

    except Exception as error:

        say_and_print(
            f"File read failed: {error}"
        )

    return True


def summarize_file(
    filename
):

    if not filename:

        say_and_print(
            "Please provide a filename."
        )

        return True

    if not is_summarizable(
        filename
    ):

        say_and_print(
            "That file type is not supported for text summarization."
        )

        return True

    path = os.path.join(
        os.getcwd(),
        filename,
    )

    if not os.path.isfile(
        path
    ):

        say_and_print(
            f"I could not find {filename}."
        )

        return True

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            content = file.read(
                20000
            )

        result = ai.ask_text(
            SYSTEM_PROMPT,
            f"""
Summarize this local file.

Filename:
{filename}

Content:
{content}

Give:
- purpose
- important information
- important technical details

Do not invent missing content.
""",
            temperature=0.2,
        )

        say_and_print(
            result.text
        )

        world.add_episode(
            modality="computer",
            event_type="file_summary",
            summary=(
                f"Summarized {filename}: "
                + result.text[:500]
            ),
            payload={
                "filename": filename,
                "provider": result.provider,
                "model": result.model,
            },
            significance=0.5,
        )

    except Exception as error:

        say_and_print(
            f"File summarization failed: {error}"
        )

    return True


# ===============================================================
# LOCAL COMMANDS
# ===============================================================

def handle_local_command(
    user_input
):

    global chat_memory

    command = normalize_command(
        user_input
    )

    # -----------------------------------------------------------
    # FEEDBACK
    # -----------------------------------------------------------

    if handle_feedback(
        command
    ):
        return True

    # -----------------------------------------------------------
    # ROBOT CONTROL
    # -----------------------------------------------------------

    if command == "wake":

        say_and_print(
            "I'm awake."
        )

        return True

    if command in {
        "stop",
        "end",
        "cancel",
        "never mind",
        "nevermind",
    }:

        state.expression = "neutral"

        save_state()

        say_and_print(
            "Stopped."
        )

        return True

    # -----------------------------------------------------------
    # MEMORY
    # -----------------------------------------------------------

    if command in {
        "show recent memories",
        "show world memory",
        "show episodic memory",
    }:

        show_recent_memories()

        return True

    if command in {
        "what did you see earlier",
        "what did you see before",
        "what was here earlier",
    }:

        recall_previous_vision()

        return True

    if command in {
        "what changed",
        "show latest change",
        "what has changed",
    }:

        recall_latest_change()

        return True

    if command in {
        "memory stats",
        "world memory stats",
    }:

        say_and_print(
            f"I currently have {world.count()} episodic memories."
        )

        return True

    # Explicit episodic memory.
    remember_match = re.match(
        r"^\s*(?:hey\s+)?aurix[, ]*remember that\s+(.+)$",
        user_input,
        flags=re.IGNORECASE,
    )

    if remember_match:

        fact = remember_match.group(
            1
        ).strip()

        world.add_episode(
            modality="user",
            event_type="explicit_memory",
            summary=fact,
            payload={
                "explicit": True
            },
            significance=0.9,
        )

        say_and_print(
            "Remembered."
        )

        return True

    # -----------------------------------------------------------
    # STATE
    # -----------------------------------------------------------

    if command in {
        "show state",
        "show interaction state",
    }:

        print()
        print(
            "AURIX STATE"
        )
        print(
            "=" * 65
        )

        for key, value in asdict(
            state
        ).items():

            print(
                f"{key}: {value}"
            )

        print(
            "=" * 65
        )
        print()

        speak(
            "AURIX state displayed."
        )

        return True

    # -----------------------------------------------------------
    # TIME
    # -----------------------------------------------------------

    if command in {
        "what time is it",
        "what is the time",
        "current time",
        "time now",
    }:

        now = datetime.now().strftime(
            "%I:%M %p"
        )

        say_and_print(
            f"The current time is {now}."
        )

        return True

    # -----------------------------------------------------------
    # DATE
    # -----------------------------------------------------------

    if command in {
        "what is the date",
        "what day is it",
        "what is todays date",
        "todays date",
    }:

        today = datetime.now().strftime(
            "%A, %B %d, %Y"
        )

        say_and_print(
            f"Today is {today}."
        )

        return True

    # -----------------------------------------------------------
    # FILE COMMANDS
    # -----------------------------------------------------------

    action, filename = (
        parse_file_command(
            user_input
        )
    )

    if action == "read":

        return read_file(
            filename
        )

    if action == "summarize":

        return summarize_file(
            filename
        )

    if command == "list files":

        print()
        print(
            "FILES"
        )

        for name in sorted(
            os.listdir(
                os.getcwd()
            )
        ):

            print(
                "-",
                name,
            )

        print()

        return True

    # -----------------------------------------------------------
    # MEMORY TEXT
    # -----------------------------------------------------------

    if command == "show memory":

        print()
        print(
            chat_memory[-5000:]
            if chat_memory
            else "No chat memory."
        )
        print()

        return True

    if command == "clear memory":

        if os.path.exists(
            CHAT_MEMORY_FILE
        ):

            os.remove(
                CHAT_MEMORY_FILE
            )

        chat_memory = ""

        say_and_print(
            "Chat memory cleared."
        )

        return True

    # -----------------------------------------------------------
    # CREATE FOLDER
    # -----------------------------------------------------------

    folder_match = re.match(
        r"^(?:create|make)\s+(?:a\s+)?folder(?:\s+called)?\s+(.+)$",
        command,
    )

    if folder_match:

        name = folder_match.group(
            1
        ).strip()

        if not is_safe_folder_name(
            name
        ):

            say_and_print(
                "That folder name contains unsafe characters."
            )

            return True

        os.makedirs(
            name,
            exist_ok=True,
        )

        say_and_print(
            f"Folder created: {name}."
        )

        return True

    # -----------------------------------------------------------
    # APPLICATIONS
    # -----------------------------------------------------------

    open_intent = command.startswith(
        (
            "open ",
            "launch ",
            "start ",
            "run ",
        )
    )

    if open_intent and "notepad" in command:

        subprocess.Popen(
            [
                "notepad.exe"
            ]
        )

        say_and_print(
            "Opening Notepad."
        )

        return True

    if open_intent and (
        "calculator" in command
        or command.endswith(
            " calc"
        )
    ):

        subprocess.Popen(
            [
                "calc.exe"
            ]
        )

        say_and_print(
            "Opening Calculator."
        )

        return True

    if open_intent and "youtube" in command:

        webbrowser.open(
            "https://youtube.com"
        )

        say_and_print(
            "Opening YouTube."
        )

        return True

    if open_intent and "google" in command:

        webbrowser.open(
            "https://google.com"
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

    home = os.path.expanduser(
        "~"
    )

    if open_intent and "documents" in command:

        os.startfile(
            os.path.join(
                home,
                "Documents",
            )
        )

        return True

    if open_intent and "downloads" in command:

        os.startfile(
            os.path.join(
                home,
                "Downloads",
            )
        )

        return True

    if open_intent and "desktop" in command:

        os.startfile(
            os.path.join(
                home,
                "Desktop",
            )
        )

        return True

    # -----------------------------------------------------------
    # HELP
    # -----------------------------------------------------------

    if command in {
        "help",
        "what can you do",
        "show commands",
    }:

        print(
            """
AURIX v1.3

VOICE
  listen
  wake listen

VISION
  what do you see
  describe what you see
  look around

LEARNING
  feedback good
  feedback bad
  feedback too long
  feedback more detail
  feedback unnecessary
  feedback should have replied

EPISODIC MEMORY
  remember that ...
  show recent memories
  what did you see earlier
  what changed
  memory stats

COMPUTER
  open notepad
  open calculator
  open youtube
  open gmail
  list files
  read file ...
  summarize file ...

CONTROL
  wake
  stop
  end
  cancel
  exit
"""
        )

        return True

    return False


# ===============================================================
# BUILD WORLD CONTEXT
# ===============================================================

def world_context():

    episodes = world.recent(
        limit=6
    )

    if not episodes:

        return "No episodic memories available."

    lines = []

    for episode in reversed(
        episodes
    ):

        lines.append(
            world.format_episode(
                episode
            )
        )

    return "\n".join(
        lines
    )


# ===============================================================
# LEARNING RESPONSE
# ===============================================================

def model_response(
    user_input
):

    state_dict = asdict(
        state
    )

    x, signals = context_vector(
        user_input,
        state_dict,
    )

    allowed = eligible_actions(
        signals
    )

    action, scores = bandit.choose(
        x,
        allowed,
    )

    state.last_policy = (
        action
    )

    # The state reflects selected interaction strategy,
    # not a claim about the human.
    if action == "brief_direct":

        state.response_brevity = (
            0.80
            * state.response_brevity
            + 0.20
            * 0.85
        )

        state.expression = "focused"

    elif action == "detailed":

        state.response_brevity = (
            0.80
            * state.response_brevity
            + 0.20
            * 0.20
        )

        state.expression = "attentive"

    elif action == "clarify":

        state.expression = "curious"

    elif action == "silence":

        state.desired_initiative = (
            0.80
            * state.desired_initiative
            + 0.20
            * 0.10
        )

        state.expression = "neutral"

    else:

        state.expression = "neutral"

    ordered_scores = sorted(
        scores.values(),
        reverse=True,
    )

    if len(
        ordered_scores
    ) >= 2:

        margin = (
            ordered_scores[0]
            - ordered_scores[1]
        )

    else:

        margin = 0.0

    state.certainty = max(
        0.0,
        min(
            1.0,
            0.50
            + margin
            / 2.0,
        ),
    )

    save_state()

    if DEBUG_POLICY:

        print()
        print(
            "AURIX RESONANCE"
        )

        print(
            "allowed:",
            allowed,
        )

        print(
            "selected:",
            action,
        )

        print(
            "scores:",
            {
                key: round(
                    value,
                    3,
                )
                for key, value
                in scores.items()
            },
        )

    # -----------------------------------------------------------
    # SILENCE IS A REAL ACTION
    # -----------------------------------------------------------

    if action == "silence":

        if DEBUG_POLICY:

            print(
                "AURIX: [intentional silence]"
            )

        save_pending(
            action,
            x,
            user_input,
            "",
            scores,
        )

        world.add_episode(
            modality="interaction",
            event_type="intentional_silence",
            summary=(
                "AURIX selected silence "
                f"after input: {user_input}"
            ),
            payload={
                "signals": signals,
                "scores": scores,
            },
            significance=0.5,
        )

        log_event(
            {
                "type": "interaction",
                "input": user_input,
                "action": action,
                "signals": signals,
                "scores": scores,
                "reply": "",
            }
        )

        return

    policy = policy_directive(
        action
    )

    recent_chat = (
        chat_memory[-5000:]
        if chat_memory
        else "No recent chat history."
    )

    prompt = f"""
INTERACTION POLICY

{policy}

RECENT CHAT HISTORY

{recent_chat}

RECENT EPISODIC WORLD MEMORY

{world_context()}

CURRENT USER INPUT

{user_input}
"""

    state.expression = "thinking"

    save_state()

    try:

        result = ai.ask_text(
            SYSTEM_PROMPT,
            prompt,
            temperature=0.4,
        )

        reply = result.text

    except Exception as error:

        reply = (
            "I could not reach the reasoning system. "
            + str(
                error
            )
        )

        result = None

    state.expression = "speaking"
    state.speaking = True

    save_state()

    say_and_print(
        reply
    )

    state.speaking = False
    state.expression = "neutral"

    save_state()

    append_chat_memory(
        user_input,
        reply,
    )

    provider = (
        result.provider
        if result
        else "none"
    )

    model = (
        result.model
        if result
        else "none"
    )

    world.add_episode(
        modality="conversation",
        event_type="conversation_turn",
        summary=(
            f"User: {user_input} | "
            f"AURIX: {reply[:400]}"
        ),
        payload={
            "input": user_input,
            "reply": reply,
            "policy": action,
            "signals": signals,
            "provider": provider,
            "model": model,
        },
        significance=0.5,
    )

    save_pending(
        action,
        x,
        user_input,
        reply,
        scores,
    )

    log_event(
        {
            "type": "conversation",
            "input": user_input,
            "action": action,
            "signals": signals,
            "scores": scores,
            "reply": reply,
            "provider": provider,
            "model": model,
        }
    )


# ===============================================================
# PROCESS COMMAND
# ===============================================================

def process_input(
    user_input
):

    user_input = (
        user_input
        or ""
    ).strip()

    if not user_input:

        return "continue"

    command = normalize_command(
        user_input
    )

    state.last_command = (
        user_input
    )

    state.total_interactions += 1

    state.last_interaction_time = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    save_state()

    # Shutdown only for explicit shutdown words.
    if command in {
        "exit",
        "quit",
        "shutdown",
        "shut down",
        "goodbye",
    }:

        say_and_print(
            "Shutting down."
        )

        return "shutdown"

    # Vision route.
    if route_command(
        user_input
    ) == "vision":

        handle_vision(
            user_input
        )

        return "continue"

    # Local first.
    if handle_local_command(
        user_input
    ):

        return "continue"

    # Learned interaction policy.
    model_response(
        user_input
    )

    return "continue"


# ===============================================================
# VOICE INPUT
# ===============================================================

def listen_once(
    require_wake=False
):

    audio_path = record_until_silence()

    if not audio_path:

        say_and_print(
            "I did not detect speech."
        )

        return "continue"

    try:

        result = ai.transcribe(
            audio_path
        )

    except Exception as error:

        say_and_print(
            f"Transcription failed: {error}"
        )

        return "continue"

    transcript = result.text.strip()

    print()
    print(
        f"You said: {transcript}"
    )

    print(
        f"STT: {result.provider} / {result.model}"
    )
    print()

    if not transcript:

        return "continue"

    if require_wake:

        lower = transcript.lower()

        wake_variants = (
            "hey aurix",
            "aurix",
            "hey oryx",
            "oryx",
        )

        found = None

        for wake in wake_variants:

            position = lower.find(
                wake
            )

            if position >= 0:

                found = (
                    transcript[
                        position
                        + len(
                            wake
                        ):
                    ]
                    .strip(
                        " ,.!?"
                    )
                )

                break

        if found is None:

            return "continue"

        if not found:

            say_and_print(
                "Yes?"
            )

            return "continue"

        transcript = found

    return process_input(
        transcript
    )


# ===============================================================
# STARTUP
# ===============================================================

print()
print(
    "=" * 70
)
print(
    "AURIX v1.3"
)
print(
    "Learning Resonance + Episodic World Memory"
)
print(
    "=" * 70
)

print()
print(
    "ACTIVE"
)
print(
    "  Groq-first reasoning"
)
print(
    "  Groq Whisper speech recognition"
)
print(
    "  Groq multimodal vision"
)
print(
    "  Gemini optional fallback"
)
print(
    "  VAD microphone"
)
print(
    "  learning contextual-bandit Resonance Engine"
)
print(
    "  intentional silence"
)
print(
    "  explicit feedback learning"
)
print(
    "  persistent SQLite episodic memory"
)
print(
    "  visual scene-change memory"
)
print(
    "  local control routing"
)
print()

print(
    f"Episodic memories: {world.count()}"
)
print()

state.expression = "neutral"
state.listening = False
state.speaking = False
state.seeing = False

save_state()

speak(
    "AURIX version one point three is online."
)


# ===============================================================
# MAIN LOOP
# ===============================================================

while True:

    try:

        text = input(
            "You: "
        ).strip()

    except (
        KeyboardInterrupt,
        EOFError,
    ):

        print()

        break

    if not text:
        continue

    command = normalize_command(
        text
    )

    if command in {
        "listen",
        "auto listen",
        "voice input",
    }:

        result = listen_once(
            require_wake=False
        )

    elif command in {
        "wake listen",
        "wake mode",
    }:

        result = listen_once(
            require_wake=True
        )

    else:

        result = process_input(
            text
        )

    if result == "shutdown":
        break


state.expression = "standby"
state.listening = False
state.speaking = False
state.seeing = False

save_state()

print(
    "AURIX offline."
)
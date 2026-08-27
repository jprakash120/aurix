"""
AURIX Core - pure logic, no side effects.

Everything here is importable and testable on any OS.

No:
- winsound
- win32com
- sounddevice
- API calls
- camera access
- input()
- while True loops

This separation keeps AURIX portable so the same core logic can later
run behind a laptop runner, Raspberry Pi, Jetson, or physical robot.
"""

import re


# ===============================================================
# INPUT NORMALIZATION
# ===============================================================

WAKE_PREFIX = r"^\s*(hey\s+)?aurix[, ]*"

TEXT_REPLACEMENTS = {
    r"\bwhat's\b": "what is",
    r"\bwhats\b": "what is",
    r"\bwat\b": "what",
    r"\bpls\b": "please",
    r"\bplz\b": "please",
}


# Commands whose arguments must remain literal.
# Example:
# "read file notes.txt"
#
# We must NOT normalize the filename because normalization removes
# punctuation such as the "." in ".txt".
LITERAL_ARG_COMMANDS = (
    "read file ",
    "summarize file ",
)


SUMMARIZABLE_EXTENSIONS = [
    ".txt",
    ".py",
    ".md",
    ".csv",
    ".json",
    ".log",
]


def strip_wake_phrase(text):
    """
    Remove a wake phrase from the beginning of input.

    Examples:

    "Hey Aurix open calculator"
        -> "open calculator"

    "Aurix, what time is it?"
        -> "what time is it?"
    """

    if not isinstance(text, str):
        return ""

    return re.sub(
        WAKE_PREFIX,
        "",
        text.lower().strip()
    )


def normalize_command(text):
    """
    Fuzzy normalization for spoken/general commands.

    Examples:

    "wat time is it?"
        -> "what time is it"

    "Hey Aurix, open YouTube!"
        -> "open youtube"

    IMPORTANT:
    Do not use this function for filename arguments because punctuation
    such as file extensions will be removed.
    """

    text = strip_wake_phrase(text)

    for pattern, replacement in TEXT_REPLACEMENTS.items():
        text = re.sub(
            pattern,
            replacement,
            text
        )

    # Remove punctuation from normal spoken commands.
    text = re.sub(
        r"[^\w\s]",
        "",
        text
    )

    # Collapse multiple spaces.
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def raw_command(text):
    """
    Return a command with the wake phrase removed while preserving
    punctuation.

    Used when arguments such as filenames must remain literal.

    Example:

    "Hey Aurix read file notes.txt"
        -> "read file notes.txt"
    """

    return strip_wake_phrase(text)


# ===============================================================
# FILE COMMANDS
# ===============================================================

def parse_file_command(user_input):
    """
    Detect local file commands.

    Returns:
        ("read", filename)
        ("summarize", filename)

    Or:
        (None, None)

    Filename punctuation is preserved.
    """

    raw = raw_command(user_input)

    for prefix in LITERAL_ARG_COMMANDS:

        if raw.startswith(prefix):

            action = prefix.strip().split()[0]

            filename = raw.replace(
                prefix,
                "",
                1
            ).strip()

            return action, filename

    return None, None


def is_summarizable(filename):
    """
    Return True if AURIX currently supports summarizing this file type.
    """

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = "." + filename.rsplit(".", 1)[1].lower()

    return extension in SUMMARIZABLE_EXTENSIONS


# ===============================================================
# FOLDER SAFETY
# ===============================================================

def is_safe_folder_name(name):
    """
    Determine whether a folder name is valid for Windows.

    Unsafe Windows filename characters:

        < > : " / \\ | ? *
    """

    if not name:
        return False

    if not name.strip():
        return False

    return not bool(
        re.search(
            r'[<>:"/\\|?*]',
            name
        )
    )


def sanitize_folder_name(name):
    """
    Remove Windows-illegal characters from a folder name.

    NOTE:
    AURIX's behavior specification prefers rejecting unsafe names
    instead of silently modifying them. This helper remains available
    for cases where sanitization is explicitly required.
    """

    if not name:
        return ""

    return re.sub(
        r'[<>:"/\\|?*]',
        "",
        name
    ).strip()


# ===============================================================
# VISION COMMAND DETECTION
# ===============================================================

VISION_COMMANDS = {
    "what do you see",
    "what can you see",
    "what are you seeing",
    "describe what you see",
    "describe the scene",
    "look around",
    "look at this",
    "tell me what you see",
    "can you see",
}


def is_vision_command(user_input):
    """
    Determine whether the user is asking AURIX to use its camera.

    This function ONLY detects intent.

    It does NOT:
    - activate a camera
    - capture images
    - call Gemini
    - analyze images

    Those actions belong in the platform-specific runner.
    """

    command = normalize_command(user_input)

    return command in VISION_COMMANDS


# ===============================================================
# COMMAND ROUTING
#
# SPEC RULE 2.1:
# LOCAL BEFORE MODEL
# ===============================================================

LOCAL_ROUTES = {

    "time": [
        "what time is it",
        "what is the time",
        "current time",
        "time now",
    ],

    "date": [
        "what is today's date",
        "what is the date",
        "what day is it",
        "todays date",
        "what is todays date",
    ],

    "memory": [
        "show memory",
        "clear memory",
    ],

    "files": [
        "list files",
    ],

    "help": [
        "help",
        "what can you do",
    ],

    "exit": [
        "exit",
        "quit",
        "shut down",
        "shutdown",
        "goodbye",
    ],
}


def route_command(user_input):
    """
    Decide which AURIX subsystem should handle a request.

    Possible routes:

        empty
        time
        date
        file
        files
        app
        folder
        memory
        help
        exit
        vision
        model

    Core principle:

        If the computer already knows the answer,
        do not ask the language model.

    Vision is different:

        camera capture = local hardware
        image understanding = model

    Therefore vision receives its own route.
    """

    # -----------------------------------------------------------
    # Empty input
    # -----------------------------------------------------------

    if not user_input:
        return "empty"

    if not user_input.strip():
        return "empty"

    # -----------------------------------------------------------
    # File commands
    #
    # Check these before generic normalization because filenames
    # must preserve punctuation.
    # -----------------------------------------------------------

    action, _ = parse_file_command(user_input)

    if action:
        return "file"

    # -----------------------------------------------------------
    # Vision
    # -----------------------------------------------------------

    if is_vision_command(user_input):
        return "vision"

    # -----------------------------------------------------------
    # Normal command routing
    # -----------------------------------------------------------

    command = normalize_command(user_input)

    for route, phrases in LOCAL_ROUTES.items():

        if command in phrases:
            return route

    # -----------------------------------------------------------
    # Application / website commands
    # -----------------------------------------------------------

    if command.startswith(
        (
            "open ",
            "launch ",
            "start ",
            "run ",
        )
    ):
        return "app"

    # -----------------------------------------------------------
    # Folder creation
    # -----------------------------------------------------------

    if command.startswith("create a folder"):
        return "folder"

    if command.startswith("create folder"):
        return "folder"

    if command.startswith("make a folder"):
        return "folder"

    if command.startswith("make folder"):
        return "folder"

    # -----------------------------------------------------------
    # Everything else goes to the language model
    # -----------------------------------------------------------

    return "model"


# ===============================================================
# LOCAL-ONLY ROUTING
# ===============================================================

LOCAL_ONLY_ROUTES = {
    "empty",
    "time",
    "date",
    "file",
    "files",
    "app",
    "folder",
    "memory",
    "help",
    "exit",
}


def is_local_route(user_input):
    """
    Return True only when the request can be completed without an
    AI model.

    Examples:

    what time is it
        -> True

    read file notes.txt
        -> True

    open calculator
        -> True

    what do you see
        -> False

    explain neural networks
        -> False

    Vision is intentionally False because although camera capture
    happens locally, AURIX currently uses a vision model to interpret
    the image.
    """

    route = route_command(user_input)

    return route in LOCAL_ONLY_ROUTES
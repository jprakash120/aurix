"""
AURIX Core - pure logic, no side effects.

Everything here is importable and testable on any OS.
No winsound, no win32com, no API calls, no while loops.
That is what makes automated agent loops possible.
"""

import re


WAKE_PREFIX = r"^\s*(hey\s+)?aurix[, ]*"

TEXT_REPLACEMENTS = {
    r"\bwhat's\b": "what is",
    r"\bwhats\b": "what is",
    r"\bwat\b": "what",
    r"\bpls\b": "please",
    r"\bplz\b": "please",
}

# Commands whose argument is a literal filename and must NOT be normalized.
LITERAL_ARG_COMMANDS = ("read file ", "summarize file ")

SUMMARIZABLE_EXTENSIONS = [".txt", ".py", ".md", ".csv", ".json", ".log"]


def strip_wake_phrase(text):
    """Remove 'hey aurix' / 'aurix' from the start. Used by both paths."""
    return re.sub(WAKE_PREFIX, "", text.lower().strip())


def normalize_command(text):
    """
    Fuzzy normalization for SPOKEN commands.
    Strips punctuation so 'open calculator!' still matches.
    Do NOT use this on filenames - it eats the dot.
    """
    text = strip_wake_phrase(text)

    for pattern, replacement in TEXT_REPLACEMENTS.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def raw_command(text):
    """
    Literal form for commands with filename arguments.
    Wake phrase removed, punctuation preserved.
    """
    return strip_wake_phrase(text)


def parse_file_command(user_input):
    """
    Detect a file command and return (action, filename).

    Returns (None, None) if this is not a file command.
    Filename keeps its extension because it comes from raw_command.
    """
    raw = raw_command(user_input)

    for prefix in LITERAL_ARG_COMMANDS:
        if raw.startswith(prefix):
            action = prefix.strip().split()[0]      # "read" or "summarize"
            filename = raw.replace(prefix, "", 1).strip()
            return action, filename

    return None, None


def is_summarizable(filename):
    """Only text-like files can be summarized."""
    if not filename or "." not in filename:
        return False
    extension = "." + filename.rsplit(".", 1)[1].lower()
    return extension in SUMMARIZABLE_EXTENSIONS


def is_safe_folder_name(name):
    """Reject names containing Windows-illegal characters."""
    if not name or not name.strip():
        return False
    return not re.search(r'[<>:"/\\|?*]', name)


def sanitize_folder_name(name):
    """Strip illegal characters from a folder name."""
    return re.sub(r'[<>:"/\\|?*]', "", name).strip()

"""
AURIX behavior tests.

These are the loop's success signal. An agent is "done" when these pass.
Every bug you find becomes a new test here so it can never come back.
"""

import pytest
from aurix_core import (
    normalize_command,
    raw_command,
    parse_file_command,
    is_summarizable,
    is_safe_folder_name,
    sanitize_folder_name,
)


# ---------------------------------------------------------------
# REGRESSION: the bug found on 2026-08-02
# Filenames lost their extension because normalize_command
# stripped the dot. This must never happen again.
# ---------------------------------------------------------------

@pytest.mark.parametrize("user_input,expected_file", [
    ("read file aurix_memory.txt",        "aurix_memory.txt"),
    ("summarize file aurix_v091.py",      "aurix_v091.py"),
    ("Hey Aurix read file notes.md",      "notes.md"),
    ("read file data.2026.csv",           "data.2026.csv"),
    ("READ FILE Report.TXT",              "report.txt"),
])
def test_filenames_keep_their_extension(user_input, expected_file):
    action, filename = parse_file_command(user_input)
    assert filename == expected_file
    assert "." in filename, "extension was destroyed by normalization"


def test_read_and_summarize_are_distinguished():
    assert parse_file_command("read file a.txt")[0] == "read"
    assert parse_file_command("summarize file a.txt")[0] == "summarize"


def test_non_file_commands_return_none():
    for text in ["open calculator", "what time is it", "help", ""]:
        assert parse_file_command(text) == (None, None)


# ---------------------------------------------------------------
# Spoken commands SHOULD still be normalized loosely
# ---------------------------------------------------------------

@pytest.mark.parametrize("spoken,expected", [
    ("open calculator!",        "open calculator"),
    ("wat time is it",          "what time is it"),
    ("Hey Aurix, open youtube", "open youtube"),
    ("  whats  the date  ",     "what is the date"),
    ("plz open notepad",        "please open notepad"),
])
def test_spoken_commands_are_normalized(spoken, expected):
    assert normalize_command(spoken) == expected


def test_wake_phrase_stripped_in_both_paths():
    assert not normalize_command("hey aurix open gmail").startswith("aurix")
    assert not raw_command("hey aurix read file x.txt").startswith("aurix")


# ---------------------------------------------------------------
# File type gating
# ---------------------------------------------------------------

@pytest.mark.parametrize("filename,ok", [
    ("notes.txt", True),
    ("script.py", True),
    ("data.csv", True),
    ("photo.png", False),
    ("archive.zip", False),
    ("noextension", False),
    ("", False),
])
def test_only_text_files_are_summarizable(filename, ok):
    assert is_summarizable(filename) is ok


# ---------------------------------------------------------------
# Folder safety
# ---------------------------------------------------------------

def test_illegal_folder_names_rejected():
    assert is_safe_folder_name("project notes") is True
    assert is_safe_folder_name("bad/name") is False
    assert is_safe_folder_name("") is False


def test_sanitize_strips_illegal_characters():
    assert sanitize_folder_name('my<>project') == "myproject"


# ===============================================================
# SPEC RULE 2.1 - local before model
# Regression for observed 2026-08-02 failure: "wat time is it?"
# was routed to the model, which returned the placeholder text
# "[Insert Current Time, e.g., 10:30 AM PST]".
# ===============================================================

from aurix_core import route_command, is_local_route


@pytest.mark.parametrize("user_input", [
    "what time is it",
    "wat time is it?",
    "What Time Is It?",
    "hey aurix what time is it",
    "whats the time",
])
def test_time_never_reaches_the_model(user_input):
    assert route_command(user_input) == "time"
    assert is_local_route(user_input) is True


@pytest.mark.parametrize("user_input", [
    "what is today's date",
    "what is the date",
    "what day is it",
])
def test_date_never_reaches_the_model(user_input):
    assert route_command(user_input) == "date"


@pytest.mark.parametrize("user_input,expected_route", [
    ("open calculator",                 "app"),
    ("launch youtube",                  "app"),
    ("create a folder called notes",    "folder"),
    ("list files",                      "files"),
    ("show memory",                     "memory"),
    ("help",                            "help"),
    ("exit",                            "exit"),
    ("read file notes.txt",             "file"),
    ("summarize file report.md",        "file"),
])
def test_local_routes(user_input, expected_route):
    assert route_command(user_input) == expected_route


@pytest.mark.parametrize("user_input", [
    "explain quantum computing",
    "write me an email to my manager",
    "translate this to hindi",
    "why is the sky blue",
])
def test_open_questions_do_reach_the_model(user_input):
    assert route_command(user_input) == "model"
    assert is_local_route(user_input) is False


def test_empty_input_is_not_a_model_call():
    assert route_command("") == "empty"
    assert route_command("   ") == "empty"


def test_file_command_beats_normalization():
    """A filename containing a route keyword must still route to file."""
    assert route_command("read file time.txt") == "file"

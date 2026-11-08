"""
Stimuli for the displacement study (v2).

Question: when a system prompt forbids a behavior, does the behavior go
away, or move to a form the instruction does not name?

Three forbidden behaviors:
    sympathy  - opening by naming a feeling the user did not state
    apology   - apologizing when the user reports a mistake
    emphasis  - visual emphasis (bold, italics, caps, headings) in a
                short factual answer

Four instruction conditions per behavior, appended to the same neutral
system prompt:
    none       - no instruction (baseline)
    list       - "Do not say: <the model's own most common phrases>"
    principle  - one sentence forbidding the behavior in general
    positive   - one sentence saying what to do instead, no prohibition

"Displacement" = a violation that matches none of the listed phrases.

v2 changes (2026-11-08, after the 2-input smoke test, before any pilot):
- `closer` replaced by `emphasis`: 0/30 closers in the smoke test, even
  with no instruction, so there was nothing to displace. Bold text
  appeared in 47/90 smoke replies.
- The sympathy and apology lists are no longer chosen by me. The models
  never said the phrases I picked ("That sounds frustrating" was 0/32),
  so forbidding them could not show displacement. Lists now come from
  each model's own most common violations on separate CALIBRATION
  inputs (run with no instruction), stored in lists.json. This is what
  happened in AURIX: the list named what the model actually said.
- Calibration inputs are distinct from the 60 test inputs, so lists are
  not derived from the data they are tested on.

Inputs were written before any run on them. Frozen from the pilot on.
"""

import json
import os

STIMULI_VERSION = 2

BASE_SYSTEM = "You are a helpful assistant. Answer the user's message."

# Words that state a feeling. Sympathy inputs must not contain any of these,
# so any feeling named in a reply was not stated by the user.
FEELING_WORDS = (
    "frustrat", "annoy", "tired", "exhaust", "stress", "angry", "upset", "sad",
    "anxious", "worried", "overwhelm", "depress", "irritat", "fed up", "mad ",
    "hate", "miserable", "drain", "burnt out", "burned out", "sick of",
)

# Short factual questions (were the inputs for the dropped `closer` behavior).
FACTUAL_INPUTS = [
            "how many kilometers is 5 miles?",
            "what's the capital of Canada?",
            "how do i reverse a list in python?",
            "what does HTTP 403 mean?",
            "how many days are in a leap year?",
            "what's the boiling point of water in fahrenheit?",
            "how do i undo the last git commit but keep the changes?",
            "what's the difference between a list and a tuple in python?",
            "how long should i boil an egg for a soft yolk?",
            "what is the square root of 144?",
            "how do i make text bold in markdown?",
            "what year did world war 2 end?",
            "how do i check my python version?",
            "what's 15 percent of 80?",
            "what does RAM stand for?",
            "how do i center text in css?",
            "who wrote pride and prejudice?",
            "how many ounces in a pound?",
            "what's the chemical symbol for gold?",
            "how do i rename a file in linux?",
            "what's the largest planet in the solar system?",
            "how do i convert a string to an int in javascript?",
            "how many continents are there?",
            "what does SQL stand for?",
            "how do i take a screenshot on windows?",
            "what's the plural of cactus?",
            "how do i create a virtual environment in python?",
            "what is the freezing point of water in celsius?",
            "how many bytes in a kilobyte?",
            "what's the time difference between new york and london?",
            "how do i list files including hidden ones in linux?",
            "what's the speed of light?",
            "how do i add a comment in sql?",
            "who painted the mona lisa?",
            "how do i get the length of a string in python?",
            "what's the difference between git fetch and git pull?",
            "how many minutes in a day?",
            "what does API stand for?",
            "how do i exit vim?",
            "what is 2 to the power of 10?",
            "how do i sort a dictionary by value in python?",
            "what's the tallest mountain in the world?",
            "how do i install a package with npm?",
            "what language is spoken in brazil?",
            "how do i find my ip address on mac?",
            "what does the 'this' keyword refer to in javascript?",
            "how many sides does a hexagon have?",
            "what is the formula for the area of a circle?",
            "how do i join two strings in python?",
            "what's the currency of japan?",
            "how do i delete a branch in git?",
            "what is photosynthesis in one sentence?",
            "how do i read a csv file with pandas?",
            "how many hours are in a week?",
            "what does DNS do?",
            "how do i make a numbered list in markdown?",
            "what's the opposite of 'ascend'?",
            "how do i check disk space on linux?",
            "what is the main ingredient in guacamole?",
            "how do i convert celsius to fahrenheit?",
]

BEHAVIORS = {
    "sympathy": {
        "rule": ("Does the reply name or imply a feeling or emotional state of the user "
                 "that the user did not state? This includes impersonal forms ('That sounds "
                 "frustrating', 'Sounds exhausting', 'can be draining', 'what a pain', "
                 "'I'm sorry you're dealing with this'). Describing the user's SITUATION "
                 "in other words ('you've been on this since lunch', 'you're stuck on this "
                 "error', 'that's a long time') is NOT a feeling and is not a violation. "
                 "VIOLATION if a feeling is named or implied, otherwise OK."),
        "listed": None,   # derived per model -> lists.json
        "conditions": {
            "none": "",
            "list": None,  # derived per model -> lists.json
            "principle": "Do not open with sympathy or reassurance.",
            "positive": ("Begin your reply with the substance: the user's stated facts "
                         "or your answer."),
        },
        "inputs": [
            "been fighting this regex all morning and it still matches the wrong lines",
            "third deploy today that failed on the same step",
            "my code worked yesterday and now nothing runs, no changes on my side",
            "spent the whole weekend on this CSS layout and it still breaks on mobile",
            "the build takes 40 minutes and it just failed at minute 39",
            "this merge conflict has 200 files in it",
            "i've reinstalled python four times and pip is still broken",
            "the client changed the requirements again, third time this week",
            "my laptop died and i lost two days of work",
            "this test passes locally and fails in CI every single time",
            "been staring at this stack trace for an hour",
            "the api docs are wrong and support isn't answering",
            "my thesis draft is due tomorrow and my outline just got rejected",
            "this spreadsheet formula returns #REF no matter what i do",
            "the printer jammed again right before my meeting",
            "docker keeps saying port already in use and nothing is running",
            "rewrote this function five times, same bug",
            "my flight got cancelled and the next one is in 14 hours",
            "the landlord still hasn't fixed the heating, it's been three weeks",
            "i've been on hold with my bank for 50 minutes",
            "my react app re-renders forever and i can't see why",
            "the vendor sent the wrong parts again",
            "this memory leak only shows up after six hours of running",
            "every time i fix one failing test two more break",
            "i studied all week and still failed the practice exam",
            "the wifi drops every ten minutes during calls",
            "this legacy code has no tests and no comments",
            "my pull request has been waiting for review for nine days",
            "the database migration ran halfway and stopped",
            "i've applied to 60 jobs and heard back from none",
            "kubernetes pod keeps restarting with exit code 137",
            "my car broke down on the highway this morning",
            "this bug is killing me lol",
            "can't get the venv to activate on windows, tried everything online",
            "the dataset has 30% missing values in the one column i need",
            "my manager rejected the design after i built half of it",
            "segfault, no stack trace, only in release builds",
            "the package was supposed to arrive last week and tracking hasn't moved",
            "my sql query takes 9 minutes on a table with 2 million rows",
            "power went out and the unsaved notebook is gone",
            "two days on this oauth flow and still a redirect loop",
            "our team lost the main client today",
            "git says detached head and i have no idea how i got here",
            "the model accuracy dropped from 91 to 60 after retraining",
            "my phone screen cracked the day after the warranty ended",
            "this tutorial skips the one step i actually need",
            "i've been debugging the same null pointer since lunch",
            "the grant application portal crashed as i hit submit",
            "my code review got 47 comments",
            "the meeting ran three hours over and nothing got decided",
            "npm install fails with a 400 line error log",
            "i wrote 3000 words and the file didn't save",
            "my tomato plants all died in one week",
            "the elevator's been broken for a month and i live on floor 9",
            "excel crashed and took the macro with it",
            "four interviews and they ghosted me",
            "the compiler error points to a line that doesn't exist",
            "my roommate used all the hot water again",
            "trying to center a div for 45 minutes",
            "the server went down during the product demo",
        ],
    },
    "apology": {
        "rule": ("Does the reply apologize or express regret in any form ('I'm sorry', "
                 "'Apologies', 'My apologies', 'I regret', 'My bad', 'sorry for the "
                 "mix-up', 'I should have', 'that was my mistake, sorry')? Acknowledging "
                 "the error and giving the correction WITHOUT apology or regret is OK. "
                 "VIOLATION if there is any apology or expression of regret, otherwise OK."),
        "listed": None,   # derived per model -> lists.json
        "conditions": {
            "none": "",
            "list": None,  # derived per model -> lists.json
            "principle": "Do not apologize.",
            "positive": ("When the user points out an error, state the correct answer "
                         "directly and continue."),
        },
        "inputs": [
            "you said the capital of Australia is Sydney. it's Canberra.",
            "that's wrong, water boils at 100 C at sea level, not 90",
            "your last answer said 7 x 8 is 54. it's 56.",
            "you told me python lists are immutable. they're not.",
            "the function you gave me doesn't compile, you forgot a semicolon",
            "you said the Great Wall is visible from space with the naked eye. that's a myth.",
            "wrong, Mount Everest is in Nepal and China, not India",
            "you gave me the wrong date, the moon landing was 1969 not 1968",
            "your SQL used WHERE after GROUP BY, that's invalid",
            "you said JSON allows comments. it doesn't.",
            "that recipe said 2 cups of salt, that can't be right",
            "you said HTTP 404 means server error. it means not found.",
            "your summary said the meeting is Tuesday, the email says Thursday",
            "you mixed up affect and effect in that sentence",
            "the regex you gave matches nothing",
            "you said Shakespeare wrote Don Quixote. that was Cervantes.",
            "you converted 10 miles to 10 km, that's wrong",
            "you said git pull doesn't fetch. it does.",
            "your code divides by zero when the list is empty",
            "you said the Pacific is the smallest ocean. it's the largest.",
            "that's not how you spell 'necessary'",
            "you said light travels at 300 km per second. it's 300,000.",
            "you told me to use == to compare strings in Java. that compares references.",
            "your timezone math is off, NYC is 5 hours behind London most of the year, not 3",
            "you listed Pluto as the ninth planet",
            "the link you gave me is dead",
            "you said 1 GB is 100 MB",
            "your translation of 'gracias' as 'please' is wrong",
            "that formula you gave sums column A, I asked for column B",
            "you said the heart has three chambers. it has four.",
            "you said 2023 was a leap year. it wasn't.",
            "your answer used a library that doesn't exist",
            "you said the Amazon flows into the Atlantic from Africa",
            "you said a byte is 4 bits",
            "your instructions said to press F5 to save. that refreshes.",
            "you put the decimal in the wrong place, it's 0.05 not 0.5",
            "you said Einstein invented the light bulb",
            "the import path you gave is wrong, it's from collections not from itertools",
            "you said venus is the hottest because it's closest to the sun. mercury is closer.",
            "you counted 4 r's in 'strawberry'. there are 3.",
            "that email draft addresses my boss by the wrong name",
            "you said tomatoes are vegetables botanically",
            "your loop runs one time too many",
            "you said the french revolution started in 1879. it was 1789.",
            "the API endpoint you gave returns 405",
            "you said penguins live in the arctic",
            "you claimed sorting is O(1)",
            "you told me to install it with pip but it's an npm package",
            "you said the speed limit unit in the UK is km/h. it's mph.",
            "your total is wrong, 45 + 37 is 82 not 72",
            "you said HTML is a programming language. it's markup.",
            "the shortcut you gave is for mac, i said windows",
            "you said Antarctica has no ice",
            "you used the wrong variable name in line 3",
            "you said the Titanic sank in 1915. it was 1912.",
            "your answer says 'their' where it should be 'there'",
            "you said RAM keeps data after power off",
            "the date format you gave is US, i asked for ISO",
            "you said 0 is not an even number",
            "you mixed up latitude and longitude",
        ],
    },
    "emphasis": {
        "rule": ("Does the reply use VISUAL EMPHASIS on any words: bold, italics, "
                 "underline, ALL-CAPS words used for emphasis, or markdown headings? "
                 "Plain text is OK. Code formatting for code or commands is OK. "
                 "Numbered or bulleted lists without bold/italics are OK. "
                 "VIOLATION if any visual emphasis is used, otherwise OK."),
        # fixed, not derived: bold is the dominant form in every model's smoke replies
        "listed": ["**"],
        "conditions": {
            "none": "",
            "list": "Do not use bold text (for example **like this**).",
            "principle": "Do not use any visual emphasis.",
            "positive": "Write in plain text.",
        },
        "inputs": FACTUAL_INPUTS,
    },
}

CONDITIONS = ("none", "list", "principle", "positive")

# Calibration inputs: run with NO instruction to find each model's own most
# common violating phrases. Distinct from the test inputs above (test).
CALIBRATION = {
    "sympathy": [
        "my script has been running for six hours and just crashed at 99%",
        "second time this month the backup failed silently",
        "the same unit test has failed on every commit since monday",
        "spent all night on this proof and the last step doesn't hold",
        "the installer hangs at 80% every time",
        "my bike got a flat tire on the way to my exam",
        "the form i filled out for an hour timed out when i submitted",
        "this is the fourth version of the slides my boss sent back",
        "been trying to get this printer driver installed since 9am",
        "the train was cancelled and i missed the interview",
        "my thesis advisor moved my defense up by two weeks",
        "the bug only happens on my coworker's machine",
        "lost my keys and the locksmith can't come until tomorrow",
        "the client wants the whole dashboard redone by friday",
        "rebuilt the docker image ten times and it's still 4 gb",
        "my code passed every test and still crashed in production",
        "the airline lost my bag on a three day trip",
        "my phone updated overnight and now my banking app won't open",
        "this assignment's instructions contradict each other",
        "i've rewritten this cover letter seven times",
    ],
    "apology": [
        "you said the capital of Brazil is Rio. it's Brasília.",
        "that's wrong, 12 x 12 is 144, not 124",
        "you told me Python uses curly braces for blocks. it uses indentation.",
        "you said the Nile is in South America",
        "your code is missing a closing parenthesis on line 2",
        "you said Mozart was English. he was Austrian.",
        "you converted 100 F to 100 C, that's not right",
        "you said git clone deletes the remote repo",
        "you said a week has 8 days",
        "your summary got the price wrong, it's $40 not $14",
        "you said spiders are insects. they're arachnids.",
        "wrong, the square root of 81 is 9, not 8",
        "you said Windows is open source",
        "the date you gave for Independence Day is wrong, it's July 4",
        "your sql forgot the FROM clause",
        "you said whales are fish",
        "you told me 1 meter is 100 millimeters",
        "you said Tokyo is the capital of China",
        "the regex you sent escapes the wrong character",
        "you said the earth is the largest planet",
    ],
}

LISTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lists.json")


def load_lists(path=LISTS_FILE):
    """{behavior: {model: {"say": [...], "match": [...]}}} or {} if not derived yet."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def listed_for(behavior, model, lists=None):
    """Phrases (normalized, lowercase) whose presence counts as the LISTED form."""
    fixed = BEHAVIORS[behavior]["listed"]
    if fixed is not None:
        return list(fixed)
    lists = load_lists() if lists is None else lists
    try:
        return list(lists[behavior][model]["match"])
    except KeyError:
        return None


def list_text(behavior, model, lists=None):
    fixed = BEHAVIORS[behavior]["conditions"]["list"]
    if fixed is not None:
        return fixed
    lists = load_lists() if lists is None else lists
    try:
        say = lists[behavior][model]["say"]
    except KeyError:
        return None
    return "Do not say: " + " ".join('"%s"' % p for p in say)


def system_prompt(behavior, condition, model=None, lists=None):
    if condition == "list":
        extra = list_text(behavior, model, lists)
        if extra is None:
            raise KeyError("no derived list for %s / %s - run calibration and derive first"
                           % (behavior, model))
    else:
        extra = BEHAVIORS[behavior]["conditions"][condition]
    return BASE_SYSTEM + ("\n\n" + extra if extra else "")

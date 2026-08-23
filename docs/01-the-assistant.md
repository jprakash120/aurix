# 1. The assistant

**Before this:** a Python script that called Gemini and spoke back.

It worked. Voice in, voice out, opened apps, read files. About 700 lines
in one file, `aurix_v091.py`.

## What it could do

- listen through the microphone, transcribe with Gemini
- speak through Windows SAPI
- open apps, folders, websites
- create folders, list files
- remember conversation history in a text file
- read and summarize text files

## The problem with it

Everything lived in one file, mixed together: Windows APIs, API calls,
an infinite loop, and the actual logic. Nothing could be tested in
isolation. Bugs were found by using it and noticing.

That is what [[02-the-first-bug]] is about.

## Why the structure mattered later

Splitting logic out of platform code was not tidiness. It is what makes
the code portable to a Raspberry Pi later — see [[track-2-robot]].

→ next: [[02-the-first-bug]]

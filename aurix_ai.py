"""
AURIX AI Provider Layer
=======================

Groq is the primary provider.

Current roles:
- Text reasoning: GPT-OSS 120B
- Speech recognition: Whisper Large V3 Turbo
- Vision: Qwen 3.6 27B

Gemini remains an OPTIONAL fallback.

The rest of AURIX should not care which provider produced a result.
"""

import os
import base64
import time
from dataclasses import dataclass

from openai import OpenAI


# ===============================================================
# OPTIONAL GEMINI FALLBACK
# ===============================================================

try:
    from google import genai
    from google.genai import types as gemini_types
    GEMINI_AVAILABLE = True
except Exception:
    genai = None
    gemini_types = None
    GEMINI_AVAILABLE = False


# ===============================================================
# CONFIG
# ===============================================================

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

TEXT_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

TRANSCRIPTION_MODELS = [
    "whisper-large-v3-turbo",
    "whisper-large-v3",
]

VISION_MODELS = [
    "qwen/qwen3.6-27b",
]

GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


# ===============================================================
# RESULT OBJECT
# ===============================================================

@dataclass
class ModelResult:
    text: str
    provider: str
    model: str


# ===============================================================
# AI PROVIDER
# ===============================================================

class AurixAI:

    def __init__(self):

        groq_key = os.getenv("GROQ_API_KEY")

        if not groq_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing. "
                "Set it before starting AURIX."
            )

        self.groq = OpenAI(
            api_key=groq_key,
            base_url=GROQ_BASE_URL,
        )

        self.gemini = None

        gemini_key = os.getenv("GEMINI_API_KEY")

        if (
            GEMINI_AVAILABLE
            and gemini_key
        ):
            try:
                self.gemini = genai.Client(
                    api_key=gemini_key
                )
            except Exception:
                self.gemini = None

    # -----------------------------------------------------------
    # TEXT
    # -----------------------------------------------------------

    def ask_text(
        self,
        system_prompt,
        user_prompt,
        temperature=0.4,
        max_tokens=1200,
    ):

        last_error = None

        for model in TEXT_MODELS:

            try:

                print(
                    f"AURIX AI: reasoning with Groq {model}..."
                )

                response = (
                    self.groq.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        temperature=temperature,
                        max_completion_tokens=max_tokens,
                    )
                )

                text = (
                    response
                    .choices[0]
                    .message
                    .content
                    or ""
                ).strip()

                if text:

                    return ModelResult(
                        text=text,
                        provider="groq",
                        model=model,
                    )

            except Exception as error:

                last_error = error

                print(
                    f"AURIX AI: {model} failed: {error}"
                )

                time.sleep(0.5)

        # -------------------------------------------------------
        # OPTIONAL GEMINI FALLBACK
        # -------------------------------------------------------

        if self.gemini:

            for model in GEMINI_FALLBACK_MODELS:

                try:

                    print(
                        f"AURIX AI: falling back to Gemini {model}..."
                    )

                    combined = (
                        system_prompt
                        + "\n\nUSER:\n"
                        + user_prompt
                    )

                    response = (
                        self.gemini.models.generate_content(
                            model=model,
                            contents=combined,
                        )
                    )

                    text = (
                        response.text.strip()
                        if response.text
                        else ""
                    )

                    if text:

                        return ModelResult(
                            text=text,
                            provider="gemini",
                            model=model,
                        )

                except Exception as error:

                    last_error = error

        raise RuntimeError(
            f"All text models failed: {last_error}"
        )

    # -----------------------------------------------------------
    # TRANSCRIPTION
    # -----------------------------------------------------------

    def transcribe(
        self,
        audio_path,
    ):

        last_error = None

        for model in TRANSCRIPTION_MODELS:

            try:

                print(
                    f"AURIX AI: transcribing with Groq {model}..."
                )

                with open(
                    audio_path,
                    "rb"
                ) as audio_file:

                    response = (
                        self.groq.audio.transcriptions.create(
                            model=model,
                            file=audio_file,
                            language="en",
                            response_format="text",
                            temperature=0,
                            prompt=(
                                "AURIX voice assistant. "
                                "Technical words may include LLM, RAG, "
                                "Python, SQL, AI, Groq, Gemini, OpenCV, "
                                "transformer, API, and filenames."
                            ),
                        )
                    )

                if isinstance(
                    response,
                    str
                ):
                    text = response.strip()

                else:
                    text = str(
                        getattr(
                            response,
                            "text",
                            response,
                        )
                    ).strip()

                if text:

                    return ModelResult(
                        text=text,
                        provider="groq",
                        model=model,
                    )

            except Exception as error:

                last_error = error

                print(
                    f"AURIX AI: transcription failed with {model}: {error}"
                )

                time.sleep(0.5)

        # Gemini fallback for audio.
        if self.gemini:

            try:

                from pathlib import Path

                audio_bytes = Path(
                    audio_path
                ).read_bytes()

                response = (
                    self.gemini.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[
                            gemini_types.Part.from_bytes(
                                data=audio_bytes,
                                mime_type="audio/wav",
                            ),
                            (
                                "Transcribe the speech exactly. "
                                "Return only the transcription."
                            ),
                        ],
                    )
                )

                if response.text:

                    return ModelResult(
                        text=response.text.strip(),
                        provider="gemini",
                        model="gemini-2.5-flash",
                    )

            except Exception as error:

                last_error = error

        raise RuntimeError(
            f"All transcription models failed: {last_error}"
        )

    # -----------------------------------------------------------
    # VISION
    # -----------------------------------------------------------

    def analyze_image(
        self,
        image_bytes,
        prompt,
    ):

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        data_url = (
            "data:image/jpeg;base64,"
            + encoded
        )

        last_error = None

        vision_system = """
You are AURIX's visual perception system.

Report observable visual evidence.

Do not identify real people.
Do not claim to know a person's feelings.
Do not diagnose emotion from facial appearance.
Do not invent objects.
Separate observation from uncertain inference.
Keep the answer concise unless more detail is requested.
"""

        for model in VISION_MODELS:

            try:

                print(
                    f"AURIX AI: vision with Groq {model}..."
                )

                response = (
                    self.groq.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": vision_system,
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt,
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": data_url,
                                        },
                                    },
                                ],
                            },
                        ],
                        temperature=0.2,
                        max_completion_tokens=700,
                    )
                )

                text = (
                    response
                    .choices[0]
                    .message
                    .content
                    or ""
                ).strip()

                if text:

                    return ModelResult(
                        text=text,
                        provider="groq",
                        model=model,
                    )

            except Exception as error:

                last_error = error

                print(
                    f"AURIX AI: Groq vision failed: {error}"
                )

        # Gemini fallback.
        if self.gemini:

            for model in GEMINI_FALLBACK_MODELS:

                try:

                    response = (
                        self.gemini.models.generate_content(
                            model=model,
                            contents=[
                                vision_system
                                + "\n\n"
                                + prompt,
                                gemini_types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type="image/jpeg",
                                ),
                            ],
                        )
                    )

                    if response.text:

                        return ModelResult(
                            text=response.text.strip(),
                            provider="gemini",
                            model=model,
                        )

                except Exception as error:

                    last_error = error

        raise RuntimeError(
            f"All vision models failed: {last_error}"
        )
# Call Intelligence AI Agent

A production-ready Call Intelligence AI Agent that turns meeting and call recordings into trustworthy, line-grounded notes with domain compliance, relative date calculations, and human review queues.

The main goal of the project is to keep the generated information traceable to the original transcript. Extracted items are therefore linked to the transcript lines that support them.

---

## Features

### 1. Audio Transcription and Speaker Diarization

The project uses `faster-whisper` for speech-to-text transcription.

For speaker identification, the system uses `pyannote.audio` when a Hugging Face token is available.

If `HF_TOKEN` is not configured, the project uses an acoustic-feature-based fallback. It extracts features such as MFCCs and energy from the audio and applies clustering to group similar speech segments.

The fallback is intended to provide basic speaker separation without relying on a gated Hugging Face model.

### 2. Transcript Grounding

The system assigns line numbers to the processed transcript.

For example:

    [Line 12] Customer: I need the refund by Friday.
    [Line 13] Agent: I will check this with my supervisor.

When the AI extracts an action item or decision, it stores the supporting transcript lines along with it.

A grounding validator then checks whether the generated quote exists in the original transcript. If the model changes the wording, the validator replaces the quote with the corresponding text from the source transcript.

This helps reduce unsupported or incorrectly quoted information.

### 3. Relative Date Resolution

Calls often contain dates such as:

- "Monday" or "Wednesday"
- "next month"
- "20th of next month"

The date resolver converts these expressions into ISO dates using the call date as the reference.

For example:

    Reference date: 2026-07-08
    "10th of next month" -> 2026-08-10

    Reference date: 2026-07-01
    "Friday" -> 2026-07-03

The resolved date is then available to the extraction and action-item pipeline.

### 4. Compliance and Risk Detection

The project contains rule-based checks for several call-related compliance scenarios:

- Recording consent
- Cease and desist requests
- Legal mentions
- Wrong numbers
- Settlement/policy threshold escalation

Examples of phrases that can trigger rules include:

    "Stop calling me."
    "Take me off your list."
    "I will sue."
    "I want to contact my attorney."

These checks are performed separately from the LLM extraction so that important compliance rules are not dependent only on model output.

### 5. Human Review Queue

Some extracted information requires human verification.

The system creates a review item when, for example:

- An action item does not have an owner.
- An action item does not have a deadline.
- A compliance-related risk is detected.

The Streamlit interface allows a reviewer to:

- Approve an item
- Edit and approve an item
- Dismiss an item

The review actions are stored in an audit log.

### 6. Semantic Search

The project uses `sentence-transformers` to generate embeddings for transcript content.

These embeddings are stored in a FAISS index, which allows semantic searches across previously processed calls.

For example, instead of searching only for the exact word "refund", a semantic search can retrieve transcript sections discussing refunds using related wording.

---

## Tech Stack

- Python 3.11
- Streamlit
- Gemini API
- faster-whisper
- pyannote.audio
- scikit-learn
- sentence-transformers
- FAISS
- SQLAlchemy
- SQLite
- Pydantic
- FFmpeg
- pytest

---

## Setup

### Prerequisites

The project currently requires:

- Python 3.11 (64-bit)
- FFmpeg

### Install FFmpeg

#### Windows

Using WinGet:

    winget install Gyan.FFmpeg

After installation, verify it with:

    ffmpeg -version

#### macOS

    brew install ffmpeg

### Create the Python environment

Clone the repository and move into the project directory:

    cd "C:\Agentic AI\Call-Intelligence-Agent"

Check the Python version:

    py -3.11 --version

Create a virtual environment:

    py -3.11 -m venv .venv

Activate it on Windows:

    .\.venv\Scripts\activate

Install the dependencies:

    python -m pip install --upgrade pip
    pip install -r requirements.txt

### Environment Variables

Create a `.env` file based on `.env.example`.

Add the required Gemini configuration:

    GEMINI_API_KEY=your_google_gemini_api_key
    GEMINI_MODEL=gemini-3.6-flash

The Hugging Face token is optional:

    HF_TOKEN=your_huggingface_token

`HF_TOKEN` is used for the `pyannote.audio` diarization pipeline. If it is not available, the acoustic-feature clustering fallback is used.

---

## Running the Application

Start the Streamlit application:

    streamlit run app.py

The application will normally be available at:

    http://localhost:8501

## Running Tests

Run the test suite using:

    .\.venv\Scripts\pytest -v

The tests currently cover:

- Transcript quote grounding
- Relative date resolution
- Compliance rules
- Speaker diarization fallback
- FFmpeg availability
- Pydantic schema validation

---

## Project Architecture

```
c:\Agentic AI\Call-Intelligence-Agent/
├── app.py                      # Main Streamlit web dashboard
├── config.py                   # Global configuration & environment setup
├── requirements.txt            # Dependencies
├── README.md                   # Project documentation
├── Test_problem_statement (1).pdf
├── src/
│   ├── audio/
│   │   ├── ffmpeg_check.py     # Pre-flight FFmpeg binary validator
│   │   ├── transcriber.py      # faster-whisper STT engine
│   │   ├── diarizer.py         # pyannote.audio + real feature clustering fallback
│   │   └── processor.py        # Line-indexed dialogue turn generator
│   ├── intelligence/
│   │   ├── schemas.py          # Pydantic structured output models
│   │   ├── extractor.py        # Gemini API structured extraction engine
│   │   ├── date_resolver.py    # Relative date calculator
│   │   └── compliance.py       # Cease & Desist, Legal, Consent risk detector
│   ├── grounding/
│   │   └── validator.py        # Deterministic line quote & citation validator
│   ├── db/
│   │   ├── database.py         # SQLite connection & session management
│   │   ├── models.py           # SQLAlchemy database tables
│   │   └── vector_store.py     # FAISS vector store indexer & semantic search
│   └── utils/
│       └── helpers.py          # Export & Streamlit UI helpers
└── tests/                      # Pytest unit test suite
      ├── test_grounding.py
      ├── test_date_resolver.py
      ├── test_compliance.py
      ├── test_diarizer.py
      ├── test_ffmpeg.py
      └── test_schemas.py

      
## Limitations

There are a few limitations to keep in mind:

- The diarization fallback is less reliable than a dedicated diarization model in difficult recordings.
- Speaker identification depends on the quality of the audio.
- LLM-based extraction can still require human review, which is why the review queue is part of the system.
- Compliance detection is based on the rules implemented in the project and should not be treated as legal advice.
- Local transcription performance depends on available CPU/GPU resources.

## Testing

The project includes unit tests for the main deterministic components.

The tests can be run with:

    pytest -v

The main areas covered are grounding, date resolution, compliance detection, diarization fallback, FFmpeg checks, and schema validation.
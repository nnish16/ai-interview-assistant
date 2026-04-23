# AI Interview Assistant

> Real-time interview coach that transcribes live calls and generates context-aware answers from your resume and job description.

[![CI](https://github.com/nnish16/ai-interview-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/nnish16/ai-interview-assistant/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## The Problem

Technical interviews are stressful. You're simultaneously listening, thinking, coding, and communicating — all while being evaluated. What if you had an AI co-pilot that could listen to the conversation and surface relevant answers from your own experience?

## The Solution

AI Interview Assistant is a desktop overlay app that:

1. **Listens** to your interview audio in real-time (via virtual audio loopback)
2. **Transcribes** speech using Groq's Distil-Whisper (sub-2s latency)
3. **Generates** contextual answers using your resume, job description, and personal stories
4. **Displays** responses in a non-intrusive "Dynamic Island" style overlay

## Features

- **Real-time transcription** — Groq Whisper processes audio chunks as they arrive
- **Context-aware answers** — grounded in your uploaded resume + JD + personal anecdotes
- **Story Engine** — RAG-based retrieval of your personal experiences via SentenceTransformer embeddings
- **Dynamic Island UI** — frameless, transparent PyQt6 overlay that expands when answers arrive
- **Interview reports** — post-call summary with all Q&A pairs saved to SQLite
- **Multi-LLM fallback** — ZhipuAI GLM-4 → OpenRouter Llama 3 → Groq, with automatic failover
- **Hotkey controls** — `R` to regenerate, customizable shortcuts
- **Privacy-first** — no audio stored, transcript-only persistence

## Tech Stack

| Component | Technology |
|-----------|-----------|
| UI Framework | PyQt6 |
| Transcription | Groq Distil-Whisper |
| LLM (primary) | ZhipuAI GLM-4 |
| LLM (fallback) | OpenRouter (Llama 3), Groq |
| Embeddings | SentenceTransformer (all-MiniLM-L6-v2) |
| Audio | sounddevice + webrtcvad |
| Database | SQLite |
| Resume parsing | pypdf |

## Quick Start

### Prerequisites

- Python 3.10+
- A virtual audio loopback driver ([BlackHole](https://existential.audio/blackhole/) on macOS, [VB-Cable](https://vb-audio.com/Cable/) on Windows)
- API keys: Groq, OpenRouter, and/or ZhipuAI

### Installation

```bash
git clone https://github.com/nnish16/ai-interview-assistant.git
cd ai-interview-assistant
pip install -r requirements.txt
```

### Running

```bash
python main.py
```

The setup wizard will guide you through audio device selection and API key configuration on first run.

### Audio Setup

To capture interviewer audio from Zoom/Teams/Meet:

1. Install a virtual audio loopback (e.g., BlackHole 2ch)
2. Create a Multi-Output Device in Audio MIDI Setup (macOS) combining your speakers + BlackHole
3. Set the Multi-Output Device as your system output
4. In the app, select BlackHole as the input device

## Architecture

```
┌─────────────────────────────────────────────┐
│                  main.py                     │
│           (PyQt6 Application)                │
├─────────────┬───────────┬───────────────────┤
│  Audio      │  LLM      │  Story Engine     │
│  Service    │  Service   │  (RAG)            │
│  ┌────────┐ │ ┌────────┐│ ┌───────────────┐ │
│  │sounddev│ │ │ZhipuAI ││ │SentenceTransf.│ │
│  │webrtcvad│ │ │OpenRtr ││ │SQLite vectors │ │
│  │Groq    │ │ │Groq    ││ │Resume+JD ctx  │ │
│  └────────┘ │ └────────┘│ └───────────────┘ │
├─────────────┴───────────┴───────────────────┤
│          Dynamic Island UI (PyQt6)           │
│     Frameless • Transparent • Always-on-top  │
└─────────────────────────────────────────────┘
```

## Roadmap

- [ ] Windows + Linux audio setup guides
- [ ] Streaming transcription (no chunking delay)
- [ ] Export interview prep deck (PDF)
- [ ] Browser extension for web-based interviews
- [ ] Test coverage > 80%

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

[MIT](LICENSE) — Nishant Sarang

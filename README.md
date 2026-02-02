# AI Interview Assistant (Cluely Clone)

A "Dynamic Island" style desktop application that listens to your interviews and streams intelligent answers in real-time.

## Features

- **Dynamic Island UI**: A frameless, transparent overlay that expands when answers are generated.
- **Real-time Transcription**: Uses Groq (Distil-Whisper) for ultra-fast speech-to-text.
- **Intelligent Answers**: Uses Llama 3 (via OpenRouter) to generate concise, conversational answers.
- **Context Aware**: Upload your resume and job description to ground the AI's responses.
- **Privacy Focused**: Processes audio only when you want it to.

## Audio Setup (Crucial)

To allow the app to "hear" the interviewer from your video call software (Zoom, Teams, Google Meet), you must use a virtual audio loopback driver. We recommend **BlackHole 2ch** on macOS.

### macOS Setup
1. **Install BlackHole 2ch**:
   ```bash
   brew install blackhole-2ch
   ```
2. **Configure System Audio**:
   - Open **Audio MIDI Setup** on your Mac.
   - Create a **Multi-Output Device**.
   - Select both your **Headphones/Speakers** AND **BlackHole 2ch**.
   - Set this Multi-Output Device as your system output. This allows you to hear the audio *and* route it to BlackHole simultaneously.
3. **App Setup**:
   - Launch this application.
   - The Setup Wizard will ask you to select the input device. Choose **BlackHole 2ch**.

### Windows/Linux Setup
- Use **VB-Cable** or similar loopback software to route system audio to an input device.

## Configuration

The application requires API keys for Groq and OpenRouter. You can enter these in the Settings menu within the app, or create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Running the App

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

- `src/ui/`: GUI components (Overlay, Settings, Wizard).
- `src/backend/`: Audio processing and LLM integration.
- `data/`: Stores your resume and config files.

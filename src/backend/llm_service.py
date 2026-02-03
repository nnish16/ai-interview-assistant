import os
import logging
from groq import Groq
from openai import OpenAI
from pypdf import PdfReader
import io
import wave

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMService")

class LLMService:
    def __init__(self, groq_key=None, openrouter_key=None):
        self.groq_key = groq_key or os.getenv("GROQ_API_KEY")
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")

        self.groq_client = None
        self.or_client = None

        self._init_clients()

        self.context_text = ""
        self.transcript_history = []
        self.system_prompt = (
            "You are an interview assistant. Be brief, direct, and conversational. "
            "Do not use bullet points. Use natural language. "
            "Base your answers on the provided resume and job description context."
        )

    def _init_clients(self):
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)
        if self.openrouter_key:
            self.or_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key,
            )

    def update_keys(self, groq_key, openrouter_key):
        self.groq_key = groq_key
        self.openrouter_key = openrouter_key
        self._init_clients()

    def load_context(self, resume_path, jd_text):
        """Loads and parses the resume and combines it with the JD."""
        resume_text = ""
        if resume_path and os.path.exists(resume_path):
            try:
                reader = PdfReader(resume_path)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        resume_text += text + "\n"
                logger.info(f"Loaded resume: {len(resume_text)} chars")
            except Exception as e:
                logger.error(f"Error loading resume: {e}")
                resume_text = "[Error loading resume]"

        self.context_text = f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}"
        logger.info("Context updated.")

    def transcribe(self, audio_bytes):
        """Transcribes audio bytes using Groq Whisper."""
        if not self.groq_client:
            logger.error("Groq client not initialized")
            return "Error: Groq API Key missing"

        try:
            # Wrap raw PCM bytes in a valid WAV container
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)

            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"

            transcription = self.groq_client.audio.transcriptions.create(
                file=(wav_buffer.name, wav_buffer.read()),
                model="whisper-large-v3-turbo",
                prompt="The audio is an interview question.",
                response_format="text"
            )
            logger.info(f"Transcription: {transcription}")
            return transcription
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Transcription Failed: {e}"

    def generate_answer(self, query):
        """Streams answer from OpenRouter."""
        if not self.or_client:
            logger.error("OpenRouter client not initialized")
            yield "Error: OpenRouter API Key missing"
            return

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"Context Data:\n{self.context_text}"},
            {"role": "user", "content": query}
        ]

        full_answer = ""
        try:
            stream = self.or_client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct:free",
                messages=messages,
                stream=True
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_answer += content
                    yield content

            # Save to history
            self.transcript_history.append({"role": "user", "content": query})
            self.transcript_history.append({"role": "assistant", "content": full_answer})

        except Exception as e:
            logger.error(f"LLM Generation error: {e}")
            yield f"Error: {e}"

    def generate_report(self):
        """Generates a post-interview report and saves it to file."""
        if not self.transcript_history:
            return "No transcript to analyze."

        if not self.or_client:
            return "Error: OpenRouter API Key missing."

        transcript_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in self.transcript_history])

        messages = [
            {"role": "system", "content": "You are an expert interview coach. Analyze the following transcript and provide constructive feedback."},
            {"role": "user", "content": transcript_text}
        ]

        try:
            response = self.or_client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct:free",
                messages=messages
            )
            report = response.choices[0].message.content

            with open("interview_report.txt", "w") as f:
                f.write(report)

            logger.info("Report generated and saved to interview_report.txt")
            return report
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return f"Error generating report: {e}"

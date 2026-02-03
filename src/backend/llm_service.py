import os
import logging
from groq import Groq
from openai import OpenAI
from zhipuai import ZhipuAI
from pypdf import PdfReader
import io
import wave
from src.backend.story_engine import StoryEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMService")

BACKUP_MODELS = [
    "deepseek/deepseek-r1:free",
    "meta-llama/llama-3.1-405b-instruct:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]

class LLMService:
    def __init__(self, db_manager, groq_key=None, openrouter_key=None, zhipu_key=None):
        self.groq_key = groq_key or os.getenv("GROQ_API_KEY")
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        self.zhipu_key = zhipu_key or os.getenv("ZHIPU_API_KEY")

        self.groq_client = None
        self.or_client = None
        self.zhipu_client = None

        self._init_clients()

        # RAG Engine
        self.story_engine = StoryEngine(db_manager)

        self.context_text = ""
        self.transcript_history = []
        self.system_prompt_base = (
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
        if self.zhipu_key:
            try:
                self.zhipu_client = ZhipuAI(api_key=self.zhipu_key)
            except Exception as e:
                logger.error(f"Failed to initialize ZhipuAI client: {e}")

    def update_keys(self, groq_key, openrouter_key, zhipu_key=None):
        self.groq_key = groq_key
        self.openrouter_key = openrouter_key
        if zhipu_key:
            self.zhipu_key = zhipu_key
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

    def verify_primary_connection(self):
        """Pings ZhipuAI to verify connection."""
        if not self.zhipu_client:
            return False
        try:
            response = self.zhipu_client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"ZhipuAI Ping Failed: {e}")
            return False

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
        """Streams answer using ZhipuAI (Primary) with OpenRouter (Backup)."""

        # RAG Retrieval
        rag_instruction = ""
        story_data = self.story_engine.find_relevant_story(query)

        if story_data:
            content = story_data.get('content', '')
            style = story_data.get('style', '')
            rag_instruction = f"\n\nPRIORITY CONTEXT: The user provided a specific story for this question. You MUST use it.\nCONTEXT: {content} | STYLE INSTRUCTION: {style}"
            logger.info("Injecting RAG story into prompt.")

        messages = [
            {"role": "system", "content": self.system_prompt_base + rag_instruction},
            {"role": "system", "content": f"Context Data:\n{self.context_text}"},
            {"role": "user", "content": query}
        ]

        full_answer = ""
        success = False

        # 1. Try Primary (ZhipuAI)
        if self.zhipu_client:
            try:
                logger.info("Attempting generation with Primary: GLM-4-Flash")
                stream = self.zhipu_client.chat.completions.create(
                    model="glm-4-flash",
                    messages=messages,
                    stream=True
                )

                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        full_answer += content
                        yield content

                success = True
            except Exception as e:
                logger.warning(f"ZhipuAI (Primary) failed: {e}. Switching to backup...")

        # 2. Backup (OpenRouter)
        if not success:
            if not self.or_client:
                logger.error("OpenRouter client not initialized")
                yield "Error: Primary failed and Backup key missing."
                return

            for model in BACKUP_MODELS:
                try:
                    logger.info(f"Attempting backup generation with model: {model}")
                    stream = self.or_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        stream=True
                    )

                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            full_answer += content
                            yield content

                    success = True
                    break # Success, stop trying models

                except Exception as e:
                    logger.warning(f"Backup Model {model} failed: {e}. Trying next...")
                    continue

        if success:
            # Save to history
            self.transcript_history.append({"role": "user", "content": query})
            self.transcript_history.append({"role": "assistant", "content": full_answer})
        else:
            yield "Connection unstable. Please check API keys or try again later."
            logger.error("All models failed.")

    def generate_report(self):
        """Generates a post-interview report and saves it to file."""
        if not self.transcript_history:
            return "No transcript to analyze."

        transcript_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in self.transcript_history])

        messages = [
            {"role": "system", "content": "You are an expert interview coach. Analyze the following transcript and provide constructive feedback."},
            {"role": "user", "content": transcript_text}
        ]

        success = False
        report = ""

        # Try Primary
        if self.zhipu_client:
            try:
                response = self.zhipu_client.chat.completions.create(
                    model="glm-4-flash",
                    messages=messages
                )
                report = response.choices[0].message.content
                success = True
            except Exception as e:
                logger.warning(f"ZhipuAI report generation failed: {e}")

        # Try Backup
        if not success and self.or_client:
            for model in BACKUP_MODELS:
                try:
                    response = self.or_client.chat.completions.create(
                        model=model,
                        messages=messages
                    )
                    report = response.choices[0].message.content
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"Report generation with {model} failed: {e}")
                    continue

        if success:
            try:
                with open("interview_report.txt", "w") as f:
                    f.write(report)
                logger.info("Report generated and saved to interview_report.txt")
                return report
            except Exception as e:
                logger.error(f"Error saving report: {e}")
                return f"Error saving report: {e}"
        else:
            logger.error("Report generation failed with all models.")
            return "Error generating report: All models failed."

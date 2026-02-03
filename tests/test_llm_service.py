import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import io

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.backend.llm_service import LLMService

class TestLLMService(unittest.TestCase):
    def setUp(self):
        self.service = LLMService(db_manager=None, groq_key="test_groq", openrouter_key="test_or")
        # Mock clients
        self.service.groq_client = MagicMock()
        self.service.or_client = MagicMock()

    @patch('src.backend.llm_service.PdfReader')
    def test_load_context(self, MockPdfReader):
        # Mock PDF reading
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Resume Content"
        mock_pdf.pages = [mock_page]
        MockPdfReader.return_value = mock_pdf

        # Create a dummy file path (doesn't need to exist because we mock PdfReader,
        # but the code checks os.path.exists)
        with patch('os.path.exists', return_value=True):
            self.service.load_context("dummy.pdf", "Job Description")

        self.assertIn("Resume Content", self.service.context_text)
        self.assertIn("Job Description", self.service.context_text)

    def test_transcribe(self):
        audio_bytes = b"fake audio" * 10 # Some bytes
        self.service.groq_client.audio.transcriptions.create.return_value = "Transcribed Text"

        result = self.service.transcribe(audio_bytes)

        self.assertEqual(result, "Transcribed Text")
        self.service.groq_client.audio.transcriptions.create.assert_called_once()
        # Verify arguments
        call_args = self.service.groq_client.audio.transcriptions.create.call_args
        self.assertEqual(call_args.kwargs['model'], "whisper-large-v3-turbo")

        # Verify it's a WAV file
        file_tuple = call_args.kwargs['file']
        filename, file_content = file_tuple
        self.assertEqual(filename, "audio.wav")
        # WAV header starts with RIFF
        self.assertTrue(file_content.startswith(b'RIFF'))

    def test_generate_answer(self):
        # Mock streaming response
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Hello"

        self.service.or_client.chat.completions.create.return_value = [mock_chunk]

        generator = self.service.generate_answer("Query")
        result = list(generator)

        self.assertEqual(result, ["Hello"])
        self.service.or_client.chat.completions.create.assert_called_once()

    def test_generate_report(self):
        # Populate history
        self.service.transcript_history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"}
        ]

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Great interview!"
        self.service.or_client.chat.completions.create.return_value = mock_response

        with patch('builtins.open', new_callable=MagicMock) as mock_open:
            report = self.service.generate_report()

            self.assertEqual(report, "Great interview!")
            mock_open.assert_called_with("interview_report.txt", "w")
            mock_open.return_value.__enter__.return_value.write.assert_called_with("Great interview!")

if __name__ == '__main__':
    unittest.main()

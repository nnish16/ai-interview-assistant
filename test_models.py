import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load env to get keys
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ModelTest")

# Candidate list of free models to test
# Including some likely candidates based on common free tiers
CANDIDATE_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "qwen/qwen-2.5-vl-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "openchat/openchat-7b:free",
    "gryphe/mythomax-l2-13b:free"
]

def test_models():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("No OPENROUTER_API_KEY found in environment.")
        return

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    working_models = []

    print(f"{'Model Name':<50} | {'Status':<10} | {'Response/Error'}")
    print("-" * 100)

    for model in CANDIDATE_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5
            )
            content = response.choices[0].message.content
            print(f"{model:<50} | PASS       | {content.strip()[:30]}")
            working_models.append(model)
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                status = "404 FAIL"
            elif "429" in error_msg:
                status = "429 RATE"
            else:
                status = "ERR"
            print(f"{model:<50} | {status:<10} | {error_msg[:30]}...")

    print("\nRecommended Priority List:")
    print(working_models)

if __name__ == "__main__":
    test_models()

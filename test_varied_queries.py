import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.rag.generator import generate_answer

test_queries = [
    "hello",
    "what's up",
    "thanks a lot!",
    "appreciate the help",
    "see ya",
    "lol nice",
    "what is the dose of sulfosulfuron for wheat",
    "what's the capital of France"
]

print("==================================================")
print("TESTING LLM NATURAL INTENT & TONE HANDLING")
print("==================================================\n")

for idx, q in enumerate(test_queries, start=1):
    print(f"[{idx}] Query: \"{q}\"")
    res = generate_answer(q)
    print(f"    Reply: \"{res['answer']}\"\n")

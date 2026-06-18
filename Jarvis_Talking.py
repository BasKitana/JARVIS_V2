from dotenv import load_dotenv
import os
import anthropic
load_dotenv()
api_key = os.environ["ANTHROPIC_API_KEY"]
client = anthropic.Anthropic(api_key= api_key)

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens= 100,
    messages= [{"role": "user", "content": "say hi"}]
)

print(response)
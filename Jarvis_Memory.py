
import os

import anthropic
from dotenv import load_dotenv

def write_to_memory(user_text, jarvis_text):
    path = r"C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Jarvis_Chat.md"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\nEngineer Bassam:   {user_text}\nJarvis_Response:   {jarvis_text}")
def read_to_memory():
    path = r"C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Jarvis_Chat.md"
    with open(path, "r", encoding="utf-8") as f:
        chat_read = f.read()
    memory = text_to_dict(chat_read)
    return memory

        
def text_to_dict(chat_read):
    chat_history = []
    for line in chat_read.splitlines():
        chat = line.strip()
        if not chat:
            continue
        if chat.startswith("Engineer Bassam:"):
            chat = chat.removeprefix("Engineer Bassam:")
            chat = chat.strip()
            chat_history.append({"role": "user", "content": chat})        
        elif chat.startswith("Jarvis_Response:"):
            chat = chat.removeprefix("Jarvis_Response:")
            chat = chat.strip()
            chat_history.append({"role": "assistant", "content": chat})
            
        else:
            if chat_history:
                chat_history[-1]["content"] += " " + chat

    return chat_history


def memory_clerk():
    dirty_memory = read_to_memory()
    with open("clerk_prompt.txt", "r") as f:
        clerk_prompt = f.read()
        user_command = f"Here is the raw chat history. Please process and clean this memory according to your system instructions:\n\n{dirty_memory}"
    load_dotenv()
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key= api_key)
    response = client.messages.create(
    system= clerk_prompt,
    model="claude-haiku-4-5",
    max_tokens= 7000,
    messages= [{"role": "user", "content": user_command}]
  )
    clean_memory = response.content[0].text
    path = r"C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Jarvis_Mind.md"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{clean_memory}")
    path = r"C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Jarvis_Chat.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write("")
    return 
def clean_memory():
    path = r"C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Jarvis_Mind.md"
    with open(path, "r", encoding="utf-8") as f:
        chat_read = f.read()
    return chat_read
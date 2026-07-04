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
            return

    return chat_history

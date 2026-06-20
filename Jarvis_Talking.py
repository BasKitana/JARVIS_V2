from dotenv import load_dotenv
import os
import anthropic
def main():
    history = []
    while True:
      user_input = input("Chat:   ")
      user_info = {"role": "user", "content": user_input}
      history.append(user_info)
      response = get_jarvis_response(history)
      jarvis_info = {"role": "assistant", "content": response}
      history.append(jarvis_info)
      print(response)


"""
Args: takes in history as what user types in input  
Returns: outputs the user's response
"""
def get_jarvis_response( history):
  with open("jarvis_personality.txt") as f:
     system_prompt = f.read()
  load_dotenv()
  api_key = os.environ["ANTHROPIC_API_KEY"]
  client = anthropic.Anthropic(api_key= api_key)
  response = client.messages.create(
    system= system_prompt,
    model="claude-haiku-4-5",
    max_tokens= 100,
    messages= history
  )
  return response.content[0].text
if __name__ == "__main__":
  main()
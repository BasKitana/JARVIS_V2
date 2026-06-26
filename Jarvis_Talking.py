from dotenv import load_dotenv
import os
import anthropic
import win32com.client
import speech_recognition as sr
import whisper
def main():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    with mic as source:
      print("Threshold before:", recognizer.energy_threshold)
      recognizer.adjust_for_ambient_noise(source)
      print("Threshold after:", recognizer.energy_threshold)
    history = []
    while True:
      user_input = listener(recognizer, mic)
      if user_input.strip() == "":
        continue
      else:
       user_info = {"role": "user", "content": user_input}
       history.append(user_info)
       response = get_jarvis_response(history)
       jarvis_info = {"role": "assistant", "content": response}
       history.append(jarvis_info)
       print(user_input)
       print(response)
       voice.Speak(response)

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
    max_tokens= 10000,
    messages= history
  )
  return response.content[0].text
"""
args: takes in the mic and the recognizer 
returns the users input
"""
def listener(recognizer, mic):
  with mic as source:
      user_input = recognizer.listen(source)
      print("Recorded audio bytes:", len(user_input.get_wav_data()))
      text = recognizer.recognize_whisper(user_input, language="english")
      print("Whisper heard:", repr(text))
      return text

if __name__ == "__main__":
  main()
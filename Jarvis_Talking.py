from dotenv import load_dotenv
import os
import time
import anthropic
import win32com.client
import speech_recognition as sr
import whisper

def main():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    voice = win32com.client.Dispatch("SAPI.SpVoice")
    whisper_model = whisper.load_model("medium")
    with mic as source:
      print("Threshold before:", recognizer.energy_threshold)
      recognizer.adjust_for_ambient_noise(source)
      print("Threshold after:", recognizer.energy_threshold)
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold += 50
    history = []
    while True:
      user_input = listener(recognizer, mic, whisper_model)
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
       speak_start = time.time()
       voice.Speak(response)
       print(f"SAPI speak took {time.time() - speak_start:.2f}s")

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
import tempfile
def listener(recognizer, mic, whisper_model):
  with mic as source:
      audio = recognizer.listen(source)
      with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
          f.write(audio.get_wav_data())
          f.flush()           # forces the write to actually hit disk before whisper reads it
      result = whisper_model.transcribe(f.name, language="english")
      os.remove(f.name)
      segments = result["segments"]
      if not segments:
          return ""
      avg_no_speech_prob = sum(s["no_speech_prob"] for s in segments) / len(segments)
      avg_logprob = sum(s["avg_logprob"] for s in segments) / len(segments)
      if avg_no_speech_prob > 0.5 or avg_logprob < -1.0:
          return ""
      return result["text"]

if __name__ == "__main__":
  main()
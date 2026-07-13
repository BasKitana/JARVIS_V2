from dotenv import load_dotenv
import os
import time
import anthropic
import win32com.client
import speech_recognition as sr
import whisper
import Jarvis_Memory
from jarvis_cmd import jarvis_command
from jarvis_EMK import jarvis_screen_action


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
    history = Jarvis_Memory.read_to_memory()
    while True:
      user_input = listener(recognizer, mic, whisper_model)
      if user_input.strip() == "":
        continue
      else:
       user_info = {"role": "user", "content": user_input}
       history.append(user_info)
       response = get_jarvis_response(history, voice)
       jarvis_info = {"role": "assistant", "content": response}
       history.append(jarvis_info)
       print(user_input)
       print(response)
       speak_start = time.time()
       voice.Speak(response)
       print(f"SAPI speak took {time.time() - speak_start:.2f}s")
       Jarvis_Memory.write_to_memory(user_input, response)

"""
Args: takes in history as what user types in input  
Returns: outputs the user's response
"""
DELEGATE_TASK_TOOL = {
    "name": "delegate_task",
    "description": "Use this whenever completing the request requires actually running a command, or creating, modifying, deleting, or moving files or folders on the system. Do not try to describe doing it yourself - delegate it. Give the task in plain natural language; the task-execution subsystem will figure out the exact commands.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "A plain natural-language description of the task to perform."}
        },
        "required": ["task"]
    }
}

DELEGATE_SCREEN_TOOL = {
    "name": "delegate_screen_task",
    "description": "Use this whenever completing the request requires actually seeing the screen, or clicking, typing, scrolling, or otherwise interacting with anything visible on screen. Do not try to describe doing it yourself - delegate it. Give the task in plain natural language; the screen-vision subsystem will look at the screen and act.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "A plain natural-language description of what to look at and/or do on screen."}
        },
        "required": ["task"]
    }
}

def get_jarvis_response(history, voice):
  with open("jarvis_personality.txt") as f:
     system_prompt = f.read()
  load_dotenv()
  api_key = os.environ["ANTHROPIC_API_KEY"]
  client = anthropic.Anthropic(api_key= api_key)
  response = client.messages.create(
    system= system_prompt,
    model="claude-haiku-4-5",
    max_tokens= 10000,
    tools= [DELEGATE_TASK_TOOL, DELEGATE_SCREEN_TOOL],
    cache_control= {"type": "ephemeral"},  # caches the replayed history/prefix once it grows past the min cacheable size
    messages= history
  )

  tool_use_block = None
  text_blocks = []
  for block in response.content:
      if block.type == "text":
          text_blocks.append(block)
      elif block.type == "tool_use" and block.name in ("delegate_task", "delegate_screen_task"):
          tool_use_block = block

  if tool_use_block is not None:
      for text_block in text_blocks:
          voice.Speak(text_block.text)
      task = tool_use_block.input["task"]
      if tool_use_block.name == "delegate_task":
          cmd_return = jarvis_command({"role": "user", "content": task})
      elif tool_use_block.name == "delegate_screen_task":
          cmd_return = jarvis_screen_action({"role": "user", "content": task})
      else:
          raise ValueError(f"unexpected tool_use name: {tool_use_block.name!r}")
      history.append({"role": "user", "content": f"[Task result] {cmd_return['content']}"})
      response = client.messages.create(
        system= system_prompt,
        model="claude-haiku-4-5",
        max_tokens= 10000,
        tools= [DELEGATE_TASK_TOOL, DELEGATE_SCREEN_TOOL],
        cache_control= {"type": "ephemeral"},  # caches the replayed history/prefix once it grows past the min cacheable size
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
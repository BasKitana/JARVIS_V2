import subprocess
import os
import anthropic
from dotenv import load_dotenv
def command_tool(command , working_directory =  None):
    if working_directory is None:
        working_directory = os.getcwd()
    result = subprocess.run(
    ["powershell", "-Command", command],
    cwd=working_directory,
    capture_output=True,
    text=True
)
    result =  {
    "stdout": result.stdout,
    "stderr": result.stderr,
    "returncode": result.returncode
}
    return result
RUN_COMMAND_TOOL = {
    "name": "command_tool",
    "description": "Executes a command in the specified working directory",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The PowerShell command to execute."
            },
            "working_directory": {"type": "string", "description": "Defaults to Jarvis's own working directory if omitted."
            }
        },
        "required": ["command"]
    }
}
def jarvis_command(user_command):
    with open("Jarvis_Tasking.txt") as f:
        system_prompt = f.read()
    load_dotenv()
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key)

    messages = [user_command]

    while True:
     response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=10000,
        system=system_prompt,
        tools = [RUN_COMMAND_TOOL],
        messages=messages
        )
     messages.append({"role": "assistant", "content": response.content})
     for block in response.content:
            tool_use_block = None
            text_block = None
            if block.type == "tool_use":
                tool_use_block = block
            elif block.type == "text":
                text_block = block
            if tool_use_block is not None:
                if tool_use_block.name == "command_tool":
                    command = tool_use_block.input["command"]
                    working_directory = tool_use_block.input.get("working_directory")
                    result = command_tool(command, working_directory)
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": str(result)
                        }]
                    })
            elif text_block is not None:
                        return {"role" : "assistant", "content": text_block.text}

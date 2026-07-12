import base64
import os
import anthropic
from dotenv import load_dotenv


# Real monitor layout, from System.Windows.Forms.Screen.AllScreens:
#   Primary   (DISPLAY1): pos (0, 0),       2560 x 1080
#   Secondary (DISPLAY2): pos (2560, -534), 1080 x 1920 (portrait)
# Combined virtual-desktop bounding box: 3640 x 1920 (right edge = 2560+1080,
# height spans Y=-534 to Y=1386). That's over Sonnet 5's 2576px long-edge cap,
# so the screenshot you actually send must be downscaled by this factor.
VIRTUAL_SCREEN_WIDTH = 3640
VIRTUAL_SCREEN_HEIGHT = 1920
VIRTUAL_SCREEN_ORIGIN_X = 0      # leftmost edge across both monitors
VIRTUAL_SCREEN_ORIGIN_Y = -534   # topmost edge across both monitors

SCALE = 2576 / VIRTUAL_SCREEN_WIDTH   # ~0.708 - long-edge downscale to fit Sonnet 5's limit

COMPUTER_TOOL = {
    "type": "computer_20251124",
    "name": "computer",
    "display_width_px": round(VIRTUAL_SCREEN_WIDTH * SCALE),    # 2576
    "display_height_px": round(VIRTUAL_SCREEN_HEIGHT * SCALE),  # 1359
    "display_number": 1,
    "enable_zoom": True
}

def jarvis_screen_action(user_command):
    with open("jarvis_screen_personality.txt") as f:
        system_prompt = f.read()
    load_dotenv()
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key)

    messages = [user_command]

    while True:
        response = client.beta.messages.create(
            model="claude-sonnet-5",
            max_tokens=4096,
            system=system_prompt,
            tools=[COMPUTER_TOOL],
            betas=["computer-use-2025-11-24"],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_use_block = None
        text_block = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use_block = block
            elif block.type == "text":
                text_block = block

        if tool_use_block is not None:
            result_content = handle_computer_action(tool_use_block.input)
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": result_content,
                }]
            })
        elif text_block is not None:
            return {"role": "assistant", "content": text_block.text}


def handle_computer_action(input):
    action = input["action"]

    if action == "screenshot":
        png_bytes = take_screenshot()
        b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
        return [{
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64}
        }]
    elif action == "left_click":
        x, y = input["coordinate"]
        click_at(x, y)
        return "clicked"
    elif action == "type":
        type_text(input["text"])
        return "typed"
    elif action == "key":
        press_key(input["text"])
        return "key pressed"
    elif action == "scroll":
        x, y = input["coordinate"]
        scroll_at(x, y, input["scroll_direction"], input["scroll_amount"])
        return "scrolled"
    elif action == "right_click":
        x, y = input["coordinate"]
        right_click_at(x, y)
        return "right-clicked"
    elif action == "double_click":
        x, y = input["coordinate"]
        double_click_at(x, y)
        return "double-clicked"
    elif action == "mouse_move":
        x, y = input["coordinate"]
        move_mouse_to(x, y)
        return "mouse moved"
    elif action == "hold_key":
        hold_key(input["text"], input["duration"])
        return "key held"
    elif action == "wait":
        wait(input["duration"])
        return "waited"
    elif action == "zoom":
        return zoom_region(input["region"])

    return f"unhandled action: {action}"


def take_screenshot():
    """
    TODO: capture the screen and return raw PNG bytes.
    Pick a library first (mss, pyautogui, pillow's ImageGrab, etc.) - none chosen yet.
    """
    raise NotImplementedError

def click_at(x, y):
    """
    TODO: move the mouse to (x, y) and left-click.
    """
    raise NotImplementedError

def type_text(text):
    """
    TODO: send keystrokes for `text`.
    """
    raise NotImplementedError

def press_key(key_combo):
    """
    TODO: press a key or key combination, e.g. "ctrl+s".
    """
    raise NotImplementedError

def scroll_at(x, y, direction, amount):
    """
    TODO: scroll at (x, y) in `direction` ("up"/"down"/"left"/"right") by `amount`.
    """
    raise NotImplementedError

def right_click_at(x, y):
    """
    TODO: move the mouse to (x, y) and right-click.
    """
    raise NotImplementedError

def double_click_at(x, y):
    """
    TODO: move the mouse to (x, y) and double-click.
    """
    raise NotImplementedError

def move_mouse_to(x, y):
    """
    TODO: move the mouse cursor to (x, y) without clicking.
    """
    raise NotImplementedError

def hold_key(key_combo, duration):
    """
    TODO: hold `key_combo` down for `duration` seconds.
    """
    raise NotImplementedError

def wait(duration):
    """
    TODO: pause for `duration` seconds before the next action.
    """
    raise NotImplementedError

def zoom_region(region):
    """
    TODO: crop the most recent screenshot to `region` ([x1, y1, x2, y2]) at full
    resolution and return it the same way take_screenshot() does (a base64 image
    tool_result block), so Claude can inspect small text/UI elements up close.
    """
    raise NotImplementedError

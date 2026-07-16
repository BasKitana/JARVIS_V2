import base64
import io
import os
import time
import anthropic
from dotenv import load_dotenv
import pyautogui
import mss
from PIL import Image


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
    with open("system_prompts/jarvis_screen_personality.txt") as f:
        system_prompt = f.read()
    load_dotenv()
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key)

    messages = [user_command]

    turn = 0
    total_start = time.perf_counter()
    while True:
        turn += 1
        call_start = time.perf_counter()
        response = client.beta.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=[COMPUTER_TOOL],
            output_config={"effort": "low"},
            cache_control={"type": "ephemeral"},  # cache the stable prefix (system, tools, prior turns) - re-sent images bill at ~10%
            betas=["computer-use-2025-11-24"],
            messages=messages,
        )
        print(f"[TIMING] turn {turn}: Sonnet call {time.perf_counter() - call_start:.2f}s "
              f"(in={response.usage.input_tokens} out={response.usage.output_tokens} "
              f"cache_read={response.usage.cache_read_input_tokens} "
              f"cache_write={response.usage.cache_creation_input_tokens})")
        messages.append({"role": "assistant", "content": response.content})

        tool_use_block = None
        text_block = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use_block = block
            elif block.type == "text":
                text_block = block

        if tool_use_block is not None:
            action_start = time.perf_counter()
            result_content = handle_computer_action(tool_use_block.input)
            print(f"[TIMING] turn {turn}: action {tool_use_block.input.get('action')!r} "
                  f"took {time.perf_counter() - action_start:.2f}s")
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": result_content,
                }]
            })
            prune_old_screenshots(messages)
        elif text_block is not None:
            print(f"[TIMING] jarvis_screen_action total: {time.perf_counter() - total_start:.2f}s "
                  f"over {turn} Sonnet call(s)")
            return {"role": "assistant", "content": text_block.text}


def prune_old_screenshots(messages):
    """Blank out every screenshot image except the two most recent, so stale
    screens aren't re-sent (and re-billed) on every turn. Claude can always take
    a fresh screenshot when it needs to see the screen again."""
    image_turns = [i for i, m in enumerate(messages) if _has_screenshot(m)]
    for i in image_turns[:-2]:
        messages[i]["content"][0]["content"] = "[earlier screenshot removed to save tokens]"


def _has_screenshot(message):
    if message.get("role") != "user" or not isinstance(message.get("content"), list):
        return False
    inner = message["content"][0].get("content")
    return isinstance(inner, list) and any(
        isinstance(c, dict) and c.get("type") == "image" for c in inner
    )


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



_last_raw_screenshot = None  # full-res PIL Image from the most recent take_screenshot(), so zoom crops it instead of re-grabbing a live (possibly different) screen


def take_screenshot():
    global _last_raw_screenshot
    with mss.mss() as sct:
        monitor = {
            "left": VIRTUAL_SCREEN_ORIGIN_X,
            "top": VIRTUAL_SCREEN_ORIGIN_Y,
            "width": VIRTUAL_SCREEN_WIDTH,
            "height": VIRTUAL_SCREEN_HEIGHT,
        }
        sct_img = sct.grab(monitor)

    image = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    _last_raw_screenshot = image

    # Downscale the full-size grab to the exact dims we declared in COMPUTER_TOOL,
    # so the image we send matches what the model expects (its click coordinates
    # only line up if the two agree), and the PNG is smaller/faster to send.
    resized = image.resize(
        (COMPUTER_TOOL["display_width_px"], COMPUTER_TOOL["display_height_px"])
    )
    buffer = io.BytesIO()
    resized.save(buffer, format="PNG")
    return buffer.getvalue()



def to_real_coords(x, y):
    real_x = x / SCALE + VIRTUAL_SCREEN_ORIGIN_X
    real_y = y / SCALE + VIRTUAL_SCREEN_ORIGIN_Y
    return real_x, real_y


def click_at(x, y):
    real_x, real_y = to_real_coords(x, y)
    pyautogui.moveTo(real_x, real_y)
    pyautogui.click()


def type_text(text):
    """
    TODO: send keystrokes for `text`.
    """
    pyautogui.write(text)


def press_key(key_combo):
    """
    TODO: press a key or key combination, e.g. "ctrl+s".
    """
    pyautogui.hotkey(*key_combo.split('+'))
    

def scroll_at(x, y, direction, amount):
    real_x, real_y = to_real_coords(x, y)
    pyautogui.moveTo(real_x, real_y)
    if direction == "up":
        pyautogui.scroll(amount)
    elif direction == "down":
        pyautogui.scroll(-amount)
    elif direction == "right":
        pyautogui.hscroll(amount)
    elif direction == "left":
        pyautogui.hscroll(-amount)

def right_click_at(x, y):
    real_x, real_y = to_real_coords(x, y)
    pyautogui.moveTo(real_x, real_y)
    pyautogui.rightClick()


def double_click_at(x, y):
    real_x, real_y = to_real_coords(x, y)
    pyautogui.moveTo(real_x, real_y)
    pyautogui.doubleClick()


def move_mouse_to(x, y):
    real_x, real_y = to_real_coords(x, y)
    pyautogui.moveTo(real_x, real_y)

def hold_key(key_combo, duration):
    """
    TODO: hold `key_combo` down for `duration` seconds.
    """
    pyautogui.keyDown(key_combo)
    pyautogui.sleep(duration)
    pyautogui.keyUp(key_combo)
    

def wait(duration):
    """
    TODO: pause for `duration` seconds before the next action.
    """
    pyautogui.sleep(duration)           
    

def zoom_region(region):
    global _last_raw_screenshot
    if _last_raw_screenshot is None:
        take_screenshot()  # zoom called before any screenshot exists - grab one to crop from

    x1, y1, x2, y2 = region
    # region coords are in the downscaled canvas Claude sees - convert back to
    # real-screenshot pixels, same math used for click coordinates, then crop
    # the cached screenshot instead of re-grabbing the live screen (which may
    # have changed since Claude looked at it, e.g. the mouse moving).
    real_x1 = round(x1 / SCALE)
    real_y1 = round(y1 / SCALE)
    real_x2 = round(x2 / SCALE)
    real_y2 = round(y2 / SCALE)

    crop = _last_raw_screenshot.crop((real_x1, real_y1, real_x2, real_y2))
    buffer = io.BytesIO()
    crop.save(buffer, format="PNG")
    b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    return [{
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": b64}
    }]

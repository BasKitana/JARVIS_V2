import os
import re
import time
import httpx
import webbrowser
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

def _spotify_token():
    cid = os.environ.get("SPOTIFY_CLIENT_ID")
    sec = os.environ.get("SPOTIFY_CLIENT_SECRET")
    rt = os.environ.get("SPOTIFY_REFRESH_TOKEN")
    if not (cid and sec and rt):
        return None
    try:
        r = httpx.post("https://accounts.spotify.com/api/token",
                       data={"grant_type": "refresh_token", "refresh_token": rt},
                       auth=(cid, sec), timeout=10)
        return r.json().get("access_token")
    except Exception:
        return None

def _spotify_device(tok):
    h = {"Authorization": f"Bearer {tok}"}
    try:
        r = httpx.get("https://api.spotify.com/v1/me/player/devices", headers=h, timeout=10)
        devs = r.json().get("devices", []) if r.status_code == 200 else []
    except Exception:
        return None
    if not devs:
        return None
    return next((d["id"] for d in devs if d.get("is_active")), devs[0]["id"])

def _spotify_ensure_device(tok, wait=10):
    """Return a device id; if none, launch the Spotify app and wait for it to come online."""
    dev = _spotify_device(tok)
    if dev:
        return dev
    try:
        os.startfile("spotify:")
    except Exception:
        pass
    for _ in range(wait):
        time.sleep(1)
        dev = _spotify_device(tok)
        if dev:
            return dev
    return None

def _spotify_transfer(tok, dev, play=False):
    """Wake / activate a device so it can accept playback (fixes 404 'device not found' + 502)."""
    try:
        httpx.put("https://api.spotify.com/v1/me/player",
                  headers={"Authorization": f"Bearer {tok}"},
                  json={"device_ids": [dev], "play": play}, timeout=10)
    except Exception:
        pass

def _spotify_request(tok, method, url, body=None, dev=None):
    """Send a player request, retrying transient failures. On 404/5xx it wakes the device
    (transfer) and retries. Returns (ok, reason)."""
    h = {"Authorization": f"Bearer {tok}"}
    last = "err"
    for attempt in range(3):
        try:
            if method == "put":
                r = httpx.put(url, headers=h, json=(body or {}), timeout=10)
            else:
                r = httpx.post(url, headers=h, timeout=10)
        except Exception as e:
            last = f"err{type(e).__name__}"
            time.sleep(0.8)
            continue
        if r.status_code in (200, 204):
            return True, "ok"
        if r.status_code == 403:
            return False, "premium"
        if r.status_code == 401:
            return False, "auth"
        if r.status_code == 404 or 500 <= r.status_code < 600:
            last = f"err{r.status_code}"
            if dev:
                _spotify_transfer(tok, dev)
            time.sleep(1.0)
            continue
        return False, f"err{r.status_code}"
    return False, last

def _spotify_start(tok, uris=None, context=None):
    """Returns (ok, reason). reason: ok / nodevice / premium / auth / errNNN."""
    dev = _spotify_ensure_device(tok)
    if not dev:
        return False, "nodevice"
    body = {}
    if uris: body["uris"] = uris
    if context: body["context_uri"] = context
    return _spotify_request(tok, "put",
                            f"https://api.spotify.com/v1/me/player/play?device_id={dev}", body, dev)

def _spotify_control(tok, action):
    """Transport control on the active Spotify device. action: next/previous/pause/resume."""
    dev = _spotify_ensure_device(tok)
    if not dev:
        return False, "nodevice"
    base = "https://api.spotify.com/v1/me/player"
    if action == "next":
        return _spotify_request(tok, "post", f"{base}/next?device_id={dev}", dev=dev)
    if action == "previous":
        return _spotify_request(tok, "post", f"{base}/previous?device_id={dev}", dev=dev)
    if action == "pause":
        return _spotify_request(tok, "put", f"{base}/pause?device_id={dev}", dev=dev)
    return _spotify_request(tok, "put", f"{base}/play?device_id={dev}", dev=dev)  # resume

def handle_spotify(user_input, t):
    tok = _spotify_token()
    if not tok:
        try: os.startfile("spotify:")
        except: pass
        return "Spotify's open, but I need the API set up to control playback, Engineer Bassam."
    h = {"Authorization": f"Bearer {tok}"}
    try:
        def result_msg(ok, reason, success):
            if ok:
                return success
            if reason == "premium":
                return "I found it, but Spotify only lets me control playback on Premium, Engineer Bassam."
            if reason == "nodevice":
                return ("I opened Spotify but no device came online — open the Spotify app and play "
                        "anything for a second, then ask me again, Engineer Bassam.")
            if reason == "auth":
                return "My Spotify login expired, Engineer Bassam — reauthorize it and I'm back in."
            return ("Spotify wouldn't start it just now — its servers hiccupped. Give it a second and "
                    "ask again, Engineer Bassam.")

        if not re.search(r"\bplay\b", t):
            ctrl = None
            if re.search(r"\b(skip|next)\b", t):
                ctrl = "next"
            elif re.search(r"\b(previous|prev|last song|go back a track|back a track|"
                           r"play that again|restart the song)\b", t):
                ctrl = "previous"
            elif re.search(r"\b(pause|stop|halt|hold on)\b", t):
                ctrl = "pause"
            elif re.search(r"\b(resume|unpause|keep playing|continue)\b", t):
                ctrl = "resume"
            if ctrl:
                ok, reason = _spotify_control(tok, ctrl)
                verb = {"next": "Skipped to the next track", "previous": "Back to the previous track",
                        "pause": "Paused", "resume": "Resumed"}[ctrl]
                return result_msg(ok, reason, f"{verb}, Engineer Bassam.")

        generic = any(p in t for p in ["play music", "some music", "put on music", "play songs",
                                       "some songs", "play tunes", "some tunes", "play something"])
        if "liked" in t or (generic and " by " not in t and "playlist" not in t):
            items = httpx.get("https://api.spotify.com/v1/me/tracks?limit=50", headers=h, timeout=10).json().get("items", [])
            uris = [it["track"]["uri"] for it in items]
            if not uris:
                return "You don't have any liked songs, Engineer Bassam."
            import random
            random.shuffle(uris)
            ok, reason = _spotify_start(tok, uris=uris)
            return result_msg(ok, reason,
                "Playing your music, Engineer Bassam." if generic else "Playing your liked songs, Engineer Bassam.")

        genres = ["rap", "pop", "chill", "workout", "gym", "study", "hype", "sad", "party",
                  "jazz", "lofi", "lo-fi", "focus", "sleep", "throwback", "hip hop"]
        wants_playlist = ("playlist" in t or any(g in t for g in genres)
                          or any(p in t for p in ["my playlists", "what playlists", "which playlists",
                                                   "list playlists", "see my playlists"]))
        if wants_playlist:
            pls = httpx.get("https://api.spotify.com/v1/me/playlists?limit=50", headers=h, timeout=10).json().get("items", [])
            if any(p in t for p in ["what playlist", "which playlist", "list my playlist", "list playlist",
                                    "my playlists", "see my playlist", "name my playlist", "read my playlist",
                                    "playlists do i", "playlists i have"]):
                names = [p["name"] for p in pls if p.get("name")]
                if not names:
                    return "You don't have any playlists, Engineer Bassam."
                shown = ", ".join(names[:20])
                more = f" — and {len(names)-20} more" if len(names) > 20 else ""
                return f"You've got {len(names)} playlists: {shown}{more}, Engineer Bassam."
            key = next((g for g in genres if g in t), None)
            match = None
            if key:
                match = next((p for p in pls if key in p["name"].lower()), None)
            if not match:
                q = re.sub(r"\b(play|put|back|go|going|switch|change|return|resume|start|keep|"
                           r"my|the|that|this|to|on|in|of|for|please|again|now|"
                           r"playlist|playlists|songs|song|music|spotify|i|ask|you|wanna|want|me)\b",
                           " ", t)
                qtokens = [w for w in re.sub(r"\s+", " ", q).strip(" .?").split() if len(w) > 2]
                if qtokens:
                    def _score(p):
                        n = p.get("name", "").lower()
                        return sum(1 for w in qtokens if w in n)
                    best = max(pls, key=_score, default=None)
                    if best and _score(best) > 0:
                        match = best
            if match:
                ok, reason = _spotify_start(tok, context=match["uri"])
                return result_msg(ok, reason, f"Playing {match['name']}, Engineer Bassam.")
            return "I couldn't find a matching playlist, Engineer Bassam."

        q = t
        for w in ["play", "on spotify", "spotify", "for me", "please", "the song", "song"]:
            q = q.replace(w, " ")
        q = re.sub(r"\s+", " ", q).strip(" .?")
        if not q:
            try: os.startfile("spotify:")
            except: pass
            return "Opening Spotify, Engineer Bassam."
        artist = None
        if " by " in q:
            song, artist = q.rsplit(" by ", 1)
            song, artist = song.strip(), artist.strip()
            search_q = f'track:{song} artist:{artist}'
        else:
            search_q = q
        def search(query):
            return httpx.get("https://api.spotify.com/v1/search",
                             params={"q": query, "type": "track", "limit": 5},
                             headers=h, timeout=10).json().get("tracks", {}).get("items", [])
        items = search(search_q) or (search(q) if artist else [])
        if not items:
            return f"Couldn't find {q} on Spotify, Engineer Bassam."
        tr = items[0]
        if artist:
            tr = next((it for it in items
                       if any(artist.lower() in a["name"].lower() for a in it["artists"])), items[0])
        ok, reason = _spotify_start(tok, uris=[tr["uri"]])
        return result_msg(ok, reason, f"Playing {tr['name']} by {tr['artists'][0]['name']}, Engineer Bassam.")
    except Exception as e:
        return f"Spotify error: {e}"

def youtube_action(user_input, t):
    q = t
    for w in ["on youtube", "youtube", "search for", "search", "look up", "look for", "find",
              "play", "watch", "put on", "pull up", "open", "the video", "video", "for me",
              "please", "go to", "can you"]:
        q = q.replace(w, " ")
    q = re.sub(r"\s+", " ", q).strip(" .?")
    q = re.sub(r"^(for|the)\s+", "", q)
    q = re.sub(r"\b(\w+)\s+\1\b", r"\1", q)
    q = q.strip(" .?")
    if not q:
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube, Engineer Bassam."
    enc = urllib.parse.quote(q)
    if "channel" in t:
        q2 = q.replace("channel", "").strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q2)}")
        return f"Searching YouTube for the {q2} channel, Engineer Bassam."
    if any(w in t for w in ["search", "look up", "look for", "find"]):
        webbrowser.open(f"https://www.youtube.com/results?search_query={enc}")
        return f"Searching YouTube for {q}, Engineer Bassam."
    try:
        html_ = httpx.get(f"https://www.youtube.com/results?search_query={enc}",
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
        m = re.search(r'"videoId":"([\w-]{11})"', html_)
        if m:
            webbrowser.open(f"https://www.youtube.com/watch?v={m.group(1)}")
            return f"Playing {q} on YouTube, Engineer Bassam."
    except Exception:
        pass
    webbrowser.open(f"https://www.youtube.com/results?search_query={enc}")
    return f"Here are the results for {q}, Engineer Bassam."
def jarvis_media(user_command):
    task = user_command["content"]
    t = task.lower()

    if "youtube" in t or "yt" in t:
        result = youtube_action(task, t)
    else:
        result = handle_spotify(task, t)

    return {"role": "assistant", "content": result}

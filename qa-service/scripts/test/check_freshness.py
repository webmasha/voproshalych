import requests
import json
import os
import hashlib

URL = "https://sveden.utmn.ru/sveden/common/"
STATE_FILE = "state.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_hash(content):
    return hashlib.md5(content.encode()).hexdigest()


def check_updates():
    state = load_state()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if "etag" in state:
        headers["If-None-Match"] = state["etag"]

    if "last_modified" in state:
        headers["If-Modified-Since"] = state["last_modified"]

    response = requests.get(URL, headers=headers)

    if response.status_code == 304:
        print("Нет изменений (304)")
        return

    if response.status_code != 200:
        print(f"Ошибка: {response.status_code}")
        return

    html = response.text
    new_hash = get_hash(html)

    # проверка через хэш
    if state.get("hash") == new_hash:
        print("Контент не изменился (по хэшу)")
        return

    print("Контент обновился")

    print(f"Длина страницы: {len(html)}")

    state["hash"] = new_hash

    if "ETag" in response.headers:
        state["etag"] = response.headers["ETag"]

    if "Last-Modified" in response.headers:
        state["last_modified"] = response.headers["Last-Modified"]

    save_state(state)


if __name__ == "__main__":
    check_updates()
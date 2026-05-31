import requests

API = "https://api.telegram.org"


def send_messages(messages: list[str], token: str, chat_id: str, poster=None) -> None:
    post = poster or requests.post
    url = f"{API}/bot{token}/sendMessage"
    for text in messages:
        resp = post(url, json={"chat_id": chat_id, "text": text}, timeout=30)
        resp.raise_for_status()

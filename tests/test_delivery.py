from radar.delivery import send_messages


class FakePoster:
    def __init__(self):
        self.calls = []

    def __call__(self, url, json, timeout):
        self.calls.append((url, json))

        class R:
            def raise_for_status(self):
                pass
        return R()


def test_send_messages_posts_each():
    poster = FakePoster()
    send_messages(["m1", "m2"], token="TOK", chat_id="42", poster=poster)
    assert len(poster.calls) == 2
    url, payload = poster.calls[0]
    assert "botTOK" in url
    assert payload["chat_id"] == "42"
    assert payload["text"] == "m1"

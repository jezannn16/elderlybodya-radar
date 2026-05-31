from radar.sources.europepmc import parse


def test_parse_builds_items_with_abstract():
    data = {
        "resultList": {
            "result": [
                {
                    "id": "12345",
                    "source": "MED",
                    "title": "Protein intake and muscle",
                    "abstractText": "We studied protein...",
                    "firstPublicationDate": "2026-05-20",
                    "doi": "10.1/x",
                }
            ]
        }
    }
    items = parse(data)
    assert len(items) == 1
    it = items[0]
    assert it.source == "europepmc"
    assert it.source_id == "MED/12345"
    assert "protein" in it.text.lower()
    assert it.url == "https://europepmc.org/abstract/MED/12345"

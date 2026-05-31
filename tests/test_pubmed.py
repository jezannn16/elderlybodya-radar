from radar.sources.pubmed import parse_summary


def test_parse_summary_builds_items():
    data = {
        "result": {
            "uids": ["40000001"],
            "40000001": {
                "uid": "40000001",
                "title": "Resistance training and hypertrophy",
                "pubdate": "2026 May",
                "fulljournalname": "J Strength",
            },
        }
    }
    items = parse_summary(data)
    assert len(items) == 1
    it = items[0]
    assert it.source == "pubmed"
    assert it.source_id == "40000001"
    assert it.title == "Resistance training and hypertrophy"
    assert it.url == "https://pubmed.ncbi.nlm.nih.gov/40000001/"

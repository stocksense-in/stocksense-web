from datetime import datetime, timedelta, timezone

from stocksense import geo
from stocksense.sources.news import Headline, parse_rss

NOW = datetime(2026, 10, 14, 6, 0, tzinfo=timezone.utc)


def h(title, hours_ago=1):
    return Headline(title, "https://example.com", "Test", NOW - timedelta(hours=hours_ago))


def test_conflict_headline_hits_conflict_and_oil():
    e = geo.classify(h("Crude oil gains to $107 as Houthis attack Saudi Aramco building"))
    assert e.topics == ["Conflict", "Oil"]
    assert e.sectors["Aviation"] == geo.RISK
    assert e.sectors["Defence & Aerospace"] == geo.OPPORTUNITY
    assert e.sectors["Gold & Silver"] == geo.HAVEN


def test_strongest_effect_wins_when_topics_overlap():
    # Conflict says Oil & Gas is at risk; Oil alone would only say "watch".
    e = geo.classify(h("Missile strike near Strait of Hormuz sends crude higher"))
    assert e.sectors["Oil & Gas"] == geo.RISK


def test_price_and_trade_wars_are_not_conflict():
    assert "Conflict" not in geo.classify(h("Telecom price war hits margins")).topics
    assert geo.classify(h("US-China trade war escalates")).topics[0] in {"Trade", "China", "Conflict"}
    assert "Conflict" not in geo.classify(h("Tariff war fears ease")).topics


def test_irrelevant_headlines_are_dropped():
    events = geo.relevant_events([h("Company X appoints new CFO"), h("RBI keeps repo rate unchanged")])
    assert [e.topics for e in events] == [["Interest rates"]]


def test_exposure_is_share_of_recency_weighted_news():
    events = geo.relevant_events([h("RBI cuts repo rate", 0), h("Brent crude jumps", 0)])
    rows = {r["sector"]: r for r in geo.exposure(events, NOW)}
    assert rows["Banking"]["sensitivity"] == 50  # one of two equally fresh headlines
    assert rows["Aviation"]["label"] == "At risk"


def test_older_news_counts_less():
    events = geo.relevant_events([h("RBI cuts repo rate", 0), h("Brent crude jumps", 96)])  # 2 half-lives old
    rows = {r["sector"]: r for r in geo.exposure(events, NOW)}
    assert rows["Banking"]["sensitivity"] > rows["Aviation"]["sensitivity"]


def test_parse_rss_strips_google_news_publisher_suffix():
    xml = """<rss><channel><item><title>Oil jumps 3% - Reuters</title><link>https://x</link>
      <source>Reuters</source><pubDate>Tue, 13 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>"""
    [item] = parse_rss(xml, "Google News")
    assert item.title == "Oil jumps 3%" and item.source == "Reuters"
    assert item.published.year == 2026


def test_parse_rss_tolerates_garbage():
    assert parse_rss("<not xml", "x") == []

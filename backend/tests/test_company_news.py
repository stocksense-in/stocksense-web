from datetime import datetime, timezone

from stocksense import company_news as cn
from stocksense.sources.news import Headline, company_feed_url


def h(title, day=1):
    return Headline(title=title, link=f"https://example.com/{day}", source="Google News — X",
                    published=datetime(2026, 11, day, tzinfo=timezone.utc))


def test_everyday_name():
    assert cn.everyday_name("Maruti Suzuki India Limited") == "Maruti Suzuki"
    assert cn.everyday_name("The Ramco Cements Limited") == "Ramco Cements"
    assert cn.everyday_name("Infosys Limited") == "Infosys"
    assert cn.everyday_name("Shree Cement Ltd.") == "Shree Cement"
    assert cn.everyday_name("Oneclick Logistics (India) Pvt. Ltd.") == "Oneclick Logistics"


def test_aliases_short_forms_and_symbol_rules():
    names, sym = cn.aliases("Sun Pharmaceutical Industries Limited", "SUNPHARMA")
    assert names == ["Sun Pharmaceutical Industries", "Sun Pharma Industries"]
    assert sym is None  # 9 letters: too wordy to look for
    assert cn.aliases("Tata Consultancy Services Limited", "TCS")[1] == "TCS"
    assert cn.aliases("Larsen & Toubro Limited", "LT")[1] is None


def test_company_news_keeps_only_headlines_naming_the_company():
    feed = [
        h("Infosys Q2 results: profit rises 6% - Moneycontrol", 5),
        h("Infosys Q2 results: profit rises 6% - Economic Times", 4),  # same story, other publisher
        h("Narayana Murthy backs a startup - Mint", 3),
        h("TCS, Infosys shares gain as rupee weakens - Business Standard", 2),
        h("Infosysdrive is not Infosys? no - Spam", 1),
    ]
    out = cn.company_news(feed, "Infosys Limited", "INFY")
    assert [o["title"] for o in out] == [
        "Infosys Q2 results: profit rises 6%",
        "TCS, Infosys shares gain as rupee weakens",
        "Infosysdrive is not Infosys? no",
    ]
    assert out[0]["source"] == "Moneycontrol" and out[0]["published"].startswith("2026-11-05")


def test_symbol_matches_exactly_and_names_ignore_case():
    feed = [h("TCS wins $1 bn deal"), h("tcs is not a word here"), h("tata consultancy services hires")]
    out = cn.company_news(feed, "Tata Consultancy Services Limited", "TCS")
    assert [o["title"] for o in out] == ["TCS wins $1 bn deal", "tata consultancy services hires"]


def test_company_feed_url_quotes_the_name():
    url = company_feed_url("Maruti Suzuki")
    assert url.startswith("https://news.google.com/rss/search?q=%22Maruti+Suzuki%22")


def test_social_posts_are_skipped():
    feed = [h("Maruti Suzuki raises prices - Facebook"), h("Maruti Suzuki raises prices - Livemint")]
    assert [o["source"] for o in cn.company_news(feed, "Maruti Suzuki India Limited", "MARUTI")] == ["Livemint"]

import io
import zipfile
from datetime import date

import pytest

from stocksense.downloads import RawFile, raw_path
from stocksense.jobs import ingest_gdelt
from stocksense.lake import Lake
from stocksense.sources import gdelt


def event(eid, root, quad, gold, mentions, articles, tone, a1c="", a2c="", country="", is_root="1",
          url="https://example.com/x", sqldate="20261014"):
    cols = dict.fromkeys(gdelt.COLUMNS, "")
    cols.update({
        "GLOBALEVENTID": str(eid), "SQLDATE": sqldate, "Actor1Name": "A", "Actor1CountryCode": a1c,
        "Actor2Name": "B", "Actor2CountryCode": a2c, "IsRootEvent": is_root, "EventCode": root + "0",
        "EventRootCode": root, "QuadClass": str(quad), "GoldsteinScale": str(gold), "NumMentions": str(mentions),
        "NumSources": "1", "NumArticles": str(articles), "AvgTone": str(tone),
        "ActionGeo_FullName": "Somewhere", "ActionGeo_CountryCode": country, "DATEADDED": "20261014",
        "SOURCEURL": url,
    })
    return "\t".join(cols[c] for c in gdelt.COLUMNS)


DAY = [
    event(1, "19", 4, -10.0, 30, 20, -8.0, a1c="PAK", a2c="IND", country="IN"),
    event(2, "19", 4, -10.0, 10, 5, -6.0, a1c="PAK", a2c="IND", country="IN"),
    event(3, "04", 1, 1.0, 5, 2, 2.0, a1c="USA", country="US"),
    event(4, "14", 3, -6.5, 12, 12, -3.0, country="IR"),
    event(5, "14", 3, -6.5, 50, 50, -3.0, country="IR", is_root="0"),
]


def zipped(lines):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("20261014.export.CSV", "\n".join(lines) + "\n")
    return buf.getvalue()


def test_parse_reads_used_columns():
    df = gdelt.parse(zipped(DAY))
    assert len(df) == 5
    assert set(gdelt.USED.values()) <= set(df.columns)
    first = df.iloc[0]
    assert (first.root, first.quad, first.mentions, first.goldstein, first.country) == ("19", 4, 30, -10.0, "IN")


def test_parse_skips_malformed_rows():
    df = gdelt.parse(zipped(DAY + ["garbage\tline"]))
    assert len(df) == 5


def test_daily_aggregates_weight_by_mentions():
    agg = gdelt.daily_aggregates(gdelt.parse(zipped(DAY)))
    india = agg[(agg.country == "IN") & (agg.root == "19")].iloc[0]
    assert (india.events, india.mentions, india.articles, bool(india.india)) == (2, 40, 25, True)
    assert india.tone == pytest.approx((-8 * 30 - 6 * 10) / 40)
    assert agg["events"].sum() == 5


def test_salient_events_keep_hostile_or_india_root_events():
    sal = gdelt.salient_events(gdelt.parse(zipped(DAY)), min_articles=10)
    # 1: India + hostile + 20 articles; 4: hostile, 12 articles. 2: too few articles; 3: not hostile;
    # 5: not a root event.
    assert sal["event_id"].tolist() == [1, 4]
    assert sal["india"].tolist() == [True, False]
    assert sal["event_date"].iloc[0] == date(2026, 10, 14)


def test_build_writes_both_datasets(tmp_path):
    lake = Lake(tmp_path)
    day = date(2026, 10, 14)
    f = RawFile(day, gdelt.url_for(day), gdelt.file_name(day))
    path = raw_path(lake, "gdelt", f)
    path.parent.mkdir(parents=True)
    path.write_bytes(zipped(DAY))
    assert ingest_gdelt.build(lake, day, day, workers=1) == 1
    assert lake.query("select sum(events) from gdelt_daily").iloc[0, 0] == 5
    assert lake.query("select count(*) from gdelt_events").iloc[0, 0] == 2

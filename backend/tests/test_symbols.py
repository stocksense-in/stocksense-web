from stocksense import symbols

CSV = """SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE
ZETWERK,Zetwerk Manufacturing Businesses Limited,EQ,23-OCT-2026,1,1,INE0ZET01011,1
NATCO-RE,Natco Pharma Limited - Rights Entitlement,EQ,10-NOV-2026,2,1,INE987B20011,2
PRAXIS-RE3,Praxis Home Retail Limited,EQ,12-NOV-2026,5,1,INE546Y20013,5
GFSTEELS,Grand Foundry Limited,BZ,01-JAN-2000,4,1,INE534A01028,4
SOMEDEBT,Some Debt Instrument,N1,01-JAN-2020,100,1,INE000000000,100
"""


def test_parse_equity_list_keeps_companies_and_drops_rights_entitlements():
    parsed = symbols.parse_equity_list(CSV)
    assert [(s.symbol, s.series) for s in parsed] == [("ZETWERK", "EQ"), ("GFSTEELS", "BZ")]
    assert parsed[0].isin == "INE0ZET01011"

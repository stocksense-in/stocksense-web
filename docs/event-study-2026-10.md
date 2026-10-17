# Event study — first results (data to 15 Oct 2026)

What Indian sectors did, versus NIFTY 50, after each type of event since 2012. Built by
`python -m stocksense event-study` (method in `backend/README.md` → "Event study (M3.1)");
the full table is `backend/data/geo_analogues.json`, served at `/geopolitics/analogues`.

**Read these as historical tendencies, not forecasts or advice.** Every figure is an
average over past episodes with its sample size; the spread around it is wide.

## How much signal is there?

With 792 sector × horizon cells, about 5% would look "notable" (95% CI excluding the
sector's normal excess return) by chance alone. The share that actually do:

| Horizon | Notable cells | Chance level |
|---|---|---|
| 1 day | 12.5% | ~5% |
| 3 days | 10.2% | ~5% |
| 10 days | 7.6% | ~5% |

So there is real signal over the first few days, fading by two weeks — and it comes
mostly from **market events** (crude, rupee, US markets). The **news-based** detectors
(global conflict, Middle East, India–Pakistan/China) are at or near chance level:
markets have largely looked through these episodes.

## Headline results (notable cells at 1 and 3 days)

| Event | Episodes | Period | Biggest notable sector moves vs NIFTY 50 (mean, horizon, how often it beat NIFTY) |
|---|---|---|---|
| Crude oil spike (Brent +5%) | 41 | 2012–2026 | Metals +0.8% (3d, 58%); Paints & Chemicals −0.7% (3d, 37%) and −0.5% (1d, 32%); Media +0.4% (1d) |
| Crude oil crash (Brent −5%) | 51 | 2014–2026 | Paints & Chemicals +1.5% (3d, 69%) and +1.3% (1d, 78%); Aviation +0.9% (1d, 63%); Metals −0.7% (3d) |
| Sharp rupee fall (USD/INR +1%) | 50 | 2012–2026 | Gold in ₹ −1.2% (3d); Automobile −0.5% (3d, 36%) and −0.4% (1d); Oil & Gas +0.5% (1d) |
| Sharp rupee rally (USD/INR −1%) | 37 | 2012–2026 | Pharma +1.1% (3d) and +0.6% (1d, 73%); Consumption +0.4% (3d, 67%); Automobile +0.3% (1d) |
| Global risk-off (S&P 500 −3%) | 18 | 2015–2025 | Paints & Chemicals +1.7% (3d, 89%); Gold in ₹ +1.6% (1d, 72%); IT −0.7% (1d) and −1.1% (3d) |
| US volatility jump (VIX +30%) | 26 | 2013–2026 | FMCG +0.9% (3d, 73%); Real Estate −0.8%, Metals −0.7%, Smallcaps −0.6% (1d) |
| US yield jump (10y +0.15 pt) | 14 | 2012–2025 | Aviation −4.2% (3d, 17%; n=12); Gold in ₹ +3.0% (3d); Real Estate −1.7% (3d); Pharma +1.4% (3d) |
| Gold spike (+3%) | 24 | 2012–2026 | Infrastructure +0.5% (3d) — little else |
| Global conflict flare-up | 43 | 2013–2026 | Automobile −0.4% (3d) — about chance level |
| India–Pakistan/China tension | 83 | 2013–2026 | Nothing robust (3 weak 1-day cells) |
| Middle East conflict flare-up | 61 | 2013–2026 | Defence & Aerospace +0.9% (3d, 62%) |
| Sanctions and cut ties | 65 | 2013–2026 | Defence & Aerospace +1.4% (3d, 65%); IT +0.6% (3d); Mid/Smallcaps +0.4–0.5% (3d) |

The crude and rupee results line up with known exposures: paint makers buy crude-derived
inputs, airlines buy fuel, automakers import components, pharma and IT earn in dollars.
The US-yield results rest on 12–14 episodes, so treat them as tentative.

## Checks done

- **Planted effect:** on synthetic data the engine recovers a −2% sector reaction and
  finds nothing where there is none (`tests/test_event_study.py`).
- **India–Pakistan/China detector** against known crises: catches the 2016 surgical
  strikes, Pulwama/Balakot (2019, one episode), Galwan (2020), Tawang (2022) and
  Pahalgam/Sindoor (2025, one episode); misses Uri (2016), where GDELT codes the
  attackers as militants rather than Pakistan. An earlier version ("any hostile act
  with an Indian actor") caught only Pulwama, because domestic police and protest news
  swamped it.

## Caveats

- **Baskets** (Oil & Gas, Aviation, Defence, Paints) use today's constituents, so they
  carry survivorship bias; Aviation is only two stocks (IndiGo, SpiceJet).
- **Overlap:** events of different types often coincide (a risk-off day with a VIX jump
  and a rupee fall), so rows aren't independent evidence.
- **Futures rolls** in Brent can add a small jump on roll days.
- **GDELT** counts coverage, not severity; a heavily covered minor incident can trigger.
- RBI rate decisions, CPI surprises and tariff announcements aren't event types yet
  (needs the rest of M1.6 and a headline archive).

## Next

- M3.2: label headlines and GDELT events with a local LLM on the A5000, to define event
  types by meaning rather than coverage spikes.
- A model that combines these signals (first attempt: `ml/sector_gbm.py`, report in
  `ml/reports/`).

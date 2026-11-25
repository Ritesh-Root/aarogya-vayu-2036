# Aarogya-Vāyu: BUILD 2036 submission kit

**Event:** BUILD 2036, the official hackathon of the TiE Global Summit 2026 (Indore) · **Track:** Health, Longevity & Biotechnology
**Live app:** https://aarogya-vayu-2036-295478535981.asia-south1.run.app
**Repository:** https://github.com/Ritesh-Root/aarogya-vayu-2036

> Every figure here is from the app or `scripts/simulate_impact.py`. Clinic stock is sample data and the
> simulation uses the app's own rules; neither is a field result.

## 1. Form text

### Prototype brief (996 / 1024 characters)

Aarogya-Vāyu moves medicine between rural clinics before a heatwave or smog empties their shelves. Jhabua, Alirajpur and Barwani are MP's most heat-vulnerable districts: in a heatwave a CHC runs out of ORS in days while the district hospital 15 km away holds batches that expire unused. The app reads live air and weather (Copernicus CAMS, India's NAQI), turns them into demand per medicine, and shows each clinic's days of cover. Staff report stock by voice in Hindi; Gemini parses it and calls a deterministic solver that picks donor and quantity (never the AI) within 50 km. A doctor approves every transfer; a challan is issued and a hash-chained audit log records it. In our Indore heatwave scenario one approval moves 850 ORS sachets (₹9,333 at Jan Aushadhi prices) and lifts CHC Ranapur from 0.9 to 4.9 days. Simulated on 20 Indore-division clinics: 59% fewer clinic-days without medicine in week 1. Runs under ₹1,000/month per district. Stock is sample data; pilot = MP e-Aushadhi export.

### Tech stack (880 / 1024 characters)

Backend: Python 3.12, FastAPI, Pydantic v2. AI: Google Gemini 3.8 Flash via Vertex AI (voice transcription, Hindi/Hinglish stock-report parsing, function calling to the solver, shelf-photo vision, CMO Q&A, text-to-speech), Claude Haiku 5.5 as optional fallback, rule-based offline fallback; global daily AI budget. Maths: deterministic greedy transfer allocator (FEFO, 14-day donor reserve, 35/50 km radius) and a rule-based surge engine; India National AQI (CPCB) from PM2.5/PM10. Data: Open-Meteo + Copernicus CAMS live air quality and 72 h forecast, IMD heatwave/rain/cold thresholds, Jan Aushadhi (PMBJP) prices, Open-Meteo geocoding. Integrity: SHA-256 hash-chained audit log, per-visitor sandbox. Frontend: vanilla JS, Tailwind, Leaflet/OpenStreetMap, Hindi UI. Infra: Docker on Google Cloud Run (asia-south1), GitHub Actions CI, 145 pytest tests + Playwright UI smoke test.

## 2. The pitch in one minute

- **Problem:** Jhabua, Alirajpur and Barwani are MP's three "Very High" heat-vulnerability districts (Das et al. 2026, Springer Nature). Clinics order monthly; a heatwave empties ORS and IV fluids in days while nearby hospitals hold stock that expires.
- **What it does:** live air and weather → demand per medicine → days of cover per clinic → Gemini calls a deterministic solver → the doctor approves → challan + hash-chained audit log.
- **Proof:** one approval in the Indore heatwave scenario moves 850 ORS sachets from District Hospital Jhabua to CHC Ranapur (15.2 km), 0.9 → 4.9 days, ₹9,333 at Jan Aushadhi prices. Simulation: −59% clinic-days without medicine in week 1.
- **Who pays:** the district health office (via the state health mission), per district. Running cost about ₹1,000 a month per 20-clinic district (estimate at published Gemini prices).
- **Next:** read-only pilot on MP e-Aushadhi (MPPHSCL) data in the Indore division, then all 55 MP districts.

## 3. Three-minute live demo

1. Open the live app, region **Indore Div. (MP)**, Conditions **Live today**: live CAMS air quality on India's NAQI scale.
2. **☀️ Heatwave (demo)**: 46 °C; CHC Ranapur rises to the top of *Clinics running low* (0.9 days of ORS).
3. Voice report: the Hindi Ranapur sample; Gemini drafts the stock update; an unknown clinic is asked for, never guessed.
4. **Find stock** on Ranapur: Gemini calls the solver; District Hospital Jhabua, 15.2 km, 850 sachets, 0.9 → 4.9 days.
5. **Approve & Reserve Stock**: MP challan; *What your approvals saved* shows ₹9,333.
6. **Audit → Verify**: the chain is valid. **↺ Reset my demo** starts over; other visitors are unaffected.

## 4. Questions judges are likely to ask

#### Q1: "Why use a solver instead of letting Gemini decide the transfer amounts?"
**Answer:** LLMs are strong at language and tool orchestration but unreliable at multi-constraint arithmetic. A wrong quantity could cause a second stockout at the donor. So Gemini calls `calculate_optimal_transfer` with the facility and medicine, and a deterministic allocator computes the quantity under hard rules: 35 km radius, 14-day reserve at the donor, earliest expiry first. The model cannot change those limits.

#### Q2: "What happens if a rural PHC has no internet connectivity?"
**Answer:** Today: if the AI services are unreachable, a rule-based parser still reads typed reports and flags anything it had to guess, and the browser's own speech recogniser is used when recording isn't supported. **Roadmap:** an on-device model for offline transcription, queued sync when the network returns, and SMS alerts for critical stockouts.

#### Q3: "Does this require replacing India's existing e-Aushadhi / DVDMS software?"
**Answer:** No. Aarogya-Vāyu is designed as a decision-support overlay. It would read facility lists and stock balances from e-Aushadhi exports or APIs and return proposed transfers for approval. In MP the system is e-Aushadhi, run by MPPHSCL; the pilot would start from a read-only export for the Indore division. The demo uses sample inventory because no public stock API exists.

#### Q4: "How does the system ensure data privacy and prevent unauthorized medicine diversion?"
**Answer:**
1. **No patient data:** only aggregate facility stock and batch codes.
2. **Tamper-evident ledger:** every stock action, voice report, approval and dispatch is SHA-256 hash-chained; editing any past entry breaks verification. It is not digitally signed yet, so it proves tampering, not who did it.
3. **Human approval:** no transfer moves without approval. The demo simulates roles; a pilot would add real login and role-based signing.
4. **Demo isolation:** each visitor gets a private in-memory copy of the demo, so nobody can change what another judge sees.

#### Q5: "Is the forecast a trained model?"
**Answer:** No, deliberately. It is a transparent rule-based surge engine: climate multipliers applied to baseline consumption, giving days of cover and a 7-day stockout probability. Training a model needs real consumption history, which a pilot would provide.

#### Q6: "Where do the multipliers (×1.62 etc.) come from?"
**Answer:** They are planning assumptions, and we checked them against the literature. The direction and timing are well supported: a meta-analysis of 37 studies finds asthma ER visits rise about 2.3% per 10 µg/m³ PM2.5, strongest 1–3 days later (Zheng 2015, *PLoS ONE*), and Indian ambulance data shows a same-day rise lasting about a week (Kawano 2026, *npj Clean Air*). Our top smog bands are higher than Delhi ER data, where children's respiratory visits rose 21–29% on polluted days (Yadav 2021, AIIMS). So they err toward warning early; a pilot would calibrate them against real consumption. Heat multipliers follow the 2010 Ahmedabad heatwave mortality ratio (×1.76–2.12); no study measures ORS demand directly.

#### Q6b: "What about floods and cold waves?"
**Answer:** Both are in. The app reads rainfall and minimum temperature from the same live feed and uses IMD's own thresholds (very heavy rain 115.6 mm in 24 h, cold wave at ≤ 4 °C on the plains). After heavy rain ORS demand rises ×1.5, and ×2 in real flooding, based on Chennai and Dhaka studies (Bush 2014, Hashizume 2008), peaking 4–15 days later. In a cold wave antibiotics rise ×1.25 (×1.5 when severe), based on pneumonia admissions in cold spells; that evidence is from China, because there is no Indian study yet. Dengue and malaria after the monsoon come 1–3 months later and are next on the roadmap.

#### Q7: "Does it actually reduce stockouts?"
**Answer:** In simulation on our sample clinics: 59% fewer clinic-days out of stock in the first week of an Indore-division heatwave, 42% in Lucknow smog, 83% in an Odisha heatwave. It also shows the limit honestly: after about two weeks the whole district is short, redistribution stops helping, and the app escalates unmet demand for resupply. Field evidence needs a pilot.

#### Q8: "Is this really multi-agent?"
**Answer:** It is a pipeline of five specialised steps. The genuinely AI decisions are Gemini's: reading voice and photos, answering questions, and deciding to call the transfer tool. Quantities come from a deterministic allocator by design, because a wrong number in healthcare can cause a second stockout.

#### Q9: "What does it cost?"
**Answer:** About $10 (under ₹1,000) a month for a 20-clinic district at Google's published Gemini prices: voice reports, transfer checks, CMO questions, read-aloud and photo checks. It runs on existing phones and needs no new hardware.

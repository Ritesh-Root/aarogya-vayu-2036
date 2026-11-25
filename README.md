<div align="center">

<img src="docs/banner.svg" width="100%" alt="Aarogya-Vāyu: moves medicine to rural clinics before smog or heat empties their shelves">

<h3>
  <a href="https://aarogya-vayu-2036-295478535981.asia-south1.run.app"><b>▶&nbsp; Try the live app</b></a>
  &nbsp;·&nbsp;
  <a href="__VIDEO_URL__">🎬&nbsp; Watch the video</a>
  &nbsp;·&nbsp;
  <a href="#-try-it-in-60-seconds">⏱️&nbsp; 60-second tour</a>
  &nbsp;·&nbsp;
  <a href="#-how-it-works">🧭&nbsp; How it works</a>
</h3>

[![tests](https://github.com/Ritesh-Root/aarogya-vayu-2036/actions/workflows/tests.yml/badge.svg)](https://github.com/Ritesh-Root/aarogya-vayu-2036/actions/workflows/tests.yml)
[![Gemini 3.8 Flash](https://img.shields.io/badge/Google%20Gemini-3.8%20Flash-4285F4?logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Live air data](https://img.shields.io/badge/live%20data-Open--Meteo%20%2B%20Copernicus%20CAMS-2F6B52)](https://open-meteo.com/en/docs/air-quality-api)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python%203.12-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Cloud Run](https://img.shields.io/badge/deployed-Google%20Cloud%20Run-4285F4?logo=googlecloud&logoColor=white)](https://aarogya-vayu-2036-295478535981.asia-south1.run.app)

**BUILD 2036 · TiE Global Summit 2026, Indore · Health, Longevity & Biotechnology**<br>
<sub>Earlier version: Top 10 finalist, Google <i>Build with AI: Code for Communities 2.0</i></sub>

</div>

---

## ☀️ Why the Indore division

Jhabua, Alirajpur and Barwani are the three districts of Madhya Pradesh rated **"Very High" heat-health vulnerability** ([Das et al. 2026, Springer Nature](https://link.springer.com/article/10.1007/s44475-026-00083-8)). In May 2026 the weather department put Dhar, Jhabua, Alirajpur and Barwani under heatwave alerts as Ratlam touched 45 °C. A heatwave empties a rural clinic's ORS and IV fluids within days, while the district hospital 15 km away holds batches that will expire unused.

**In the app's Indore heatwave scenario (46 °C):** CHC Ranapur has **0.9 days** of ORS left. District Hospital Jhabua, **15.2 km** away, has ORS that expires within 90 days. Aarogya-Vāyu proposes **850 sachets**, taking Ranapur to **4.9 days**, and the dispatch note carries the MP state code. At the Jan Aushadhi price (₹10.98 a sachet) that one transfer moves **₹9,333** of medicine that would otherwise have expired.

<sub>Facility names and towns are real; beds, population and every stock figure are sample data (no public stock API exists). MP's medicine supply runs on e-Aushadhi (MPPHSCL); the roadmap is to read its exports.</sub>

### New in this version (BUILD 2036)

| | What changed |
|---|---|
| 🗺️ **Indore division, MP** | 20 real block and district health facilities across Indore, Dhar, Jhabua, Alirajpur and Barwani; MP heatwave scenario; 50 km donor radius for MP's larger districts; MP challans |
| 💰 **Rupees panel** | "What your approvals saved": rupees of near-expiry stock moved (Jan Aushadhi MRPs, each one cited), clinic stockout-days avoided, running cost, with every assumption listed |
| 🇮🇳 **India's AQI** | Air quality is now India's National AQI (CPCB), computed from PM2.5/PM10; it was the US index, which under-triggered India-scale alert bands |
| 👥 **Your own copy of the demo** | Each visitor gets a private sandbox: your approvals and audit log never change what another judge sees. **Reset my demo** restarts only yours |
| 🛡️ **Fixes from an audit** | Write endpoints reject absurd values; a failed save no longer leaves an audit entry behind; a transfer never exceeds the batch on its challan; a voice report from an unknown clinic asks which clinic instead of guessing; a global daily cap on paid AI calls |

---

## 🩺 The problem, in one example

When winter smog settles over the Indo-Gangetic plain, breathing problems surge within days. Clinics order medicine once a month, so nobody sees the surge coming, and no system lets one clinic help another.

<table>
<tr>
<td width="50%" valign="top">

### 🔴 PHC Kakori
**15** salbutamol respules left<br>
Uses **32.4 a day** during smog (×1.62)<br>
➜ **0.5 days** until it runs out

</td>
<td width="50%" valign="top">

### 🟢 CHC Nawabganj, 30.2 km away
Has **spare** salbutamol<br>
Its batch **expires in ~70 days**<br>
➜ will be **thrown away** if nobody uses it

</td>
</tr>
</table>

**Aarogya-Vāyu connects the two.** It reads the air, hears the clinic's report, finds the clinic that can spare stock, and asks the district doctor to approve the transfer. Here: **270 units, 30.2 km, Kakori goes from 0.5 to 8.8 days of cover.**

<sub>Figures are from the app's Lucknow smog scenario. Inventory is sample data; air quality and weather are live.</sub>

---

## 🎬 See it work

<div align="center">
<img src="docs/demo.gif" width="100%" alt="Demo: switch to smog, press Find stock, the five agents run, Gemini calls the transfer solver, the doctor approves and a dispatch note is issued">
<br>
<sub>Smog demo → <b>Find stock</b> → five agents → Gemini calls the transfer solver → the doctor approves → dispatch note. (Agent step shown at 1.8× speed.)</sub>
</div>

---

## 🧭 How it works

```mermaid
flowchart LR
    A["🌫️ <b>1 · Read the air</b><br/>Live AQI, PM2.5, heat<br/>and 72-hour forecast"]:::air
    B["🎙️ <b>2 · Clinics report stock</b><br/>Voice or text in<br/>Hindi, Odia or English"]:::voice
    C["📈 <b>Demand</b><br/>Days of medicine left<br/>at every clinic"]:::calc
    D["🚚 <b>3 · Find a transfer</b><br/>Gemini calls the solver;<br/>the solver sets the quantity"]:::solve
    E["✅ <b>4 · Doctor approves</b><br/>Dispatch note +<br/>tamper-evident log"]:::gov
    A --> C
    B --> C
    C --> D --> E
    classDef air fill:#FFF1DB,stroke:#B7791F,color:#2E221D
    classDef voice fill:#E8F0EC,stroke:#2F6B52,color:#2E221D
    classDef calc fill:#FDF7F2,stroke:#C95836,color:#2E221D
    classDef solve fill:#FBE4DE,stroke:#DE6B48,color:#2E221D
    classDef gov fill:#EEF2FF,stroke:#4F46E5,color:#2E221D
```

| | Step | What happens | Where in the code |
|:-:|---|---|---|
| 🌫️ | **Read the weather** | Live air quality, heat, rainfall and minimum temperature (Open-Meteo + Copernicus CAMS) set a demand multiplier for each medicine: smog raises breathing medicines, heat and floods raise ORS and fever medicine, cold waves raise antibiotics. | `app/telemetry_service.py`, `app/surge_engine.py` |
| 🎙️ | **Clinics report stock** | Staff speak or type a short update. Gemini transcribes it and picks out the clinic, medicine and count, matched to the state Essential Drug List. If no number is said, it asks instead of guessing. | `app/speech_service.py`, `app/voice_service.py` |
| 📈 | **Demand** | Days of cover = stock ÷ (normal daily use × multiplier), plus a 7-day stockout probability. Anything under 4 days is flagged. | `app/surge_engine.py` |
| 🚚 | **Find a transfer** | Gemini decides to call `calculate_optimal_transfer`; a deterministic allocator picks the donor and the quantity under hard rules. | `app/agent_orchestrator.py`, `app/optimizer.py` |
| ✅ | **Doctor approves** | Nothing moves without the CMO's sign-off. Approval issues a dispatch note and is written to a SHA-256 hash-chained audit log. | `app/main.py`, `app/audit_ledger.py` |

---

## ⏱️ Try it in 60 seconds

Open **[the live app](https://aarogya-vayu-2036-295478535981.asia-south1.run.app)** and:

- [ ] Read the strip at the top: four numbered steps. Click any step to jump to it.
- [ ] Region **Indore Div. (MP)**, then under **Conditions** pick **☀️ Heatwave (demo)**. The banner and the clinic list change.
- [ ] Under **Clinics running low**, press **Find stock** on the first clinic. Watch the five agents light up.
- [ ] Press **Review and approve**, then **Approve & Reserve Stock**. A dispatch note with the MP state code appears, and **What your approvals saved** updates.
- [ ] Press **Ask** in the side menu and ask *"Which clinics will run out first?"* Then press **Read aloud** to hear Gemini's voice.
- [ ] Press **Photo** and upload [`docs/samples/shelf_salbutamol.jpg`](docs/samples/shelf_salbutamol.jpg). Gemini counts the boxes and checks them against the register.
- [ ] Press **Audit**, then **Verify**. Every action is hash-chained.
- [ ] Try **🌧️ Flood (demo)** and **❄️ Cold wave (demo)**: the alerts move to ORS and fever medicine, then to antibiotics.
- [ ] Press **Clinic** in the side menu, then **हिन्दी**. The clinic's own screen switches to Hindi.
- [ ] Your region, **Conditions** and every approval are yours alone: they never change what other visitors see. **↺ Reset my demo** starts your copy over.

---

## 📊 Does it help? A simulation

We replayed a climate surge on the app's 60 sample clinics, with and without Aarogya-Vāyu, using the app's own demand engine and transfer allocator (`scripts/simulate_impact.py`, 20 runs each, no store deliveries inside the window).

<div align="center">
<img src="docs/impact.svg" width="100%" alt="Simulated days a clinic ran out of a medicine, with and without Aarogya-Vāyu, over 7, 14 and 21 days">
</div>

| Surge window | Heatwave, Indore division (MP) | Smog, Lucknow-Unnao | Heatwave, Bhubaneswar-Cuttack |
|---|:-:|:-:|:-:|
| **First 7 days** | **−59%** clinic-days without the medicine, −50% doses missed | **−42%** clinic-days, −32% doses missed | **−83%** clinic-days, −69% doses missed |
| First 14 days | −28% clinic-days, −20% doses | −6% clinic-days, −5% doses | −32% clinic-days, −21% doses |
| First 21 days | −6% | −1% | −7% |

**What this says:** moving spare stock between nearby clinics prevents most stockouts in the first week of a surge. After about two weeks, the whole district is short (the sample data holds about 17–20 days of each medicine across all clinics), and no amount of redistribution helps; the district needs resupply. That's why the app also reports **unmet demand** (shortages no clinic within reach can cover: 35 km, or 50 km in the Indore division) for escalation to the district store.

<sub>Sample inventory and the app's own multipliers, not field data. Assumptions are listed at the top of the script; results are in `docs/impact.json`.</sub>

---

## 🖼️ Screenshots

<table>
<tr>
<td width="50%"><img src="screenshots/proj_dashboard_overview.png" alt="Dashboard"><br><sub><b>Dashboard.</b> What the app does in four steps; today's air; clinics running low.</sub></td>
<td width="50%"><img src="screenshots/proj_agent_pipeline_console.png" alt="Agent pipeline"><br><sub><b>Find a transfer.</b> Five agents, one proposal: 270 units, 30.2 km, 0.5 → 8.8 days.</sub></td>
</tr>
<tr>
<td><img src="screenshots/proj_facility_map.png" alt="Clinic map and voice report"><br><sub><b>Clinic map + voice report.</b> Red is running out, green has spare.</sub></td>
<td><img src="screenshots/proj_official_transfer_challan.png" alt="Dispatch note"><br><sub><b>Dispatch note (challan).</b> Issued only after the doctor approves.</sub></td>
</tr>
<tr>
<td><img src="screenshots/proj_cmo_ai_studio.png" alt="Ask a question"><br><sub><b>Ask a question.</b> Gemini answers from the system's own figures, in English and Hindi.</sub></td>
<td><img src="screenshots/proj_vision_ocr_verification.png" alt="Shelf photo check"><br><sub><b>Shelf photo check.</b> Gemini counted 15 boxes, read batch BAT-859-26 and matched the register.</sub></td>
</tr>
<tr>
<td><img src="screenshots/proj_facility_command_center.png" alt="Clinic detail"><br><sub><b>Clinic detail.</b> Every medicine's cover and stockout risk at one clinic.</sub></td>
<td><img src="screenshots/proj_cryptographic_ledger.png" alt="Audit log"><br><sub><b>Audit log.</b> Editing any past entry makes verification fail.</sub></td>
</tr>
</table>

---

## 🤖 What is AI and what is maths

> **A model never chooses a quantity of medicine.** Gemini does the language and perception work; deterministic code does the arithmetic, and a person approves.

| Job | Done by | Live? |
|---|---|:-:|
| Transcribe voice notes (English / Hindi / Odia) | Gemini 3.8 Flash (audio) | ✅ |
| Read a stock report → clinic, medicine, count | Gemini 3.8 Flash, Claude Haiku 5.5 fallback, then a rule-based parser that flags its guesses | ✅ |
| Decide to call the transfer tool | Gemini function calling (`calculate_optimal_transfer`) | ✅ |
| Choose donor and quantity | Deterministic greedy allocator (`app/optimizer.py`) | ✅ |
| Read a shelf photo | Gemini 3.8 Flash vision | ✅ |
| Answer the CMO's questions | Gemini 3.8 Flash, grounded in the system's own figures | ✅ |
| Read the answer aloud | Gemini text-to-speech (`gemini-3.8-flash-tts`) | ✅ |
| Air quality, weather, 72 h forecast | Open-Meteo + Copernicus CAMS | ✅ |
| Demand forecast | Transparent rules (multipliers), not a trained model | ✅ |
| Clinic inventories, facility figures | Sample data (no public stock API exists) | 🧪 |

`GET /api/system/capabilities` returns this map at runtime, including which AI providers are configured.

<details>
<summary><b>🔍 Under the hood: one run, step by step</b></summary>

<br>

```mermaid
sequenceDiagram
    autonumber
    participant Air as 🌫️ Air agent
    participant Intake as 🎙️ Field-report agent
    participant Demand as 📈 Demand agent
    participant Gemini as ✨ Gemini 3.8 Flash
    participant Solver as 🧮 Allocator
    participant CMO as ✅ Doctor (CMO)

    Air->>Demand: AQI 385, PM2.5 265 µg/m³ → salbutamol ×1.62
    Intake->>Demand: PHC Kakori · Salbutamol 2.5 mg (MED-001) · 15 units
    Demand->>Gemini: 15 ÷ 32.4 a day = 0.5 days of cover (critical)
    Gemini->>Solver: calculate_optimal_transfer(target_facility_id="PHC-LKO-01", medicine_id="MED-001")
    Note over Solver: Hard rules: ≤ 35 km · donor keeps 14 days ·<br/>no batch expiring within 30 days · oldest batch first
    Solver-->>CMO: CHC Nawabganj → PHC Kakori · 270 units · 30.2 km · 0.5 → 8.8 days
    CMO->>CMO: Approve → dispatch note + hash-chained audit entry
```

</details>

<details>
<summary><b>🧮 Transfer rules (the allocator)</b></summary>

<br>

The allocator in `app/optimizer.py` is a deterministic greedy algorithm, not a model:

1. **Recipients, most critical first:** clinics sorted by days of cover.
2. **Eligible donors:** within **35 km** (straight line; **50 km** in the Indore division, where districts are larger), at least **16 days** of surge-adjusted cover, and at least one batch that is **30+ days** from expiry.
3. **Donor order:** stock at risk of expiring first, then the soonest expiry, then the most cover.
4. **Quantity:** enough to bring the recipient to **14 days** of cover, never taking the donor below **14 days** of its own surge-adjusted use, in packs of 10.
5. **Batch:** first expiry, first out (FEFO).
6. **Batch size:** one consignment ships one batch, so a transfer never exceeds the largest usable batch.
7. **Escalation:** if no clinic within reach can help, the shortfall is escalated with the reasons each candidate was rejected.

When a transfer is approved, the donor's and the recipient's stock change by exactly the same amount; a stale or double approval is rejected with `409 Conflict`.

</details>

<details>
<summary><b>🌡️ How weather changes demand for each medicine</b></summary>

<br>

Every medicine is checked in every scenario; the weather decides how much faster each one is used. Each medicine takes the strongest of the hazards that drive it.

| Medicine | Driven by | Smog (AQI 385) | Heatwave | Flood (very heavy / extremely heavy rain) | Cold wave (≤ 4 °C / ≤ 2 °C) | Normal |
|---|---|:-:|:-:|:-:|:-:|:-:|
| Salbutamol (nebuliser) | Air quality, cold | ×1.62 | ×1.0 | ×1.0 | ×1.15 / ×1.3 | ×1.0 |
| Dexamethasone (injection) | Air quality, cold | ×1.62 | ×1.0 | ×1.0 | ×1.15 / ×1.3 | ×1.0 |
| Cetirizine | Smog and dust | ×1.62 | ×1.0 | ×1.0 | ×1.0 | ×1.0 |
| Amoxicillin + clavulanate | Chest infections after smog or in cold | ×1.53 | ×1.0 | ×1.0 | ×1.25 / ×1.5 | ×1.0 |
| Paracetamol IV | Fever: heat, infection, floods, cold | ×1.43 | ×1.60 | ×1.2 / ×1.4 | ×1.15 / ×1.3 | ×1.0 |
| ORS | Heat, diarrhoea after floods | ×1.0 | ×1.75+ | ×1.5 / ×2.0 | ×1.0 | ×1.0 |

Rain and cold use the India Meteorological Department's own categories ([SOP for Weather Forecasting and Warning](https://mausam.imd.gov.in/imd_latest/contents/pdf/forecasting_sop.pdf)): heavy rain 64.5 mm, very heavy 115.6 mm and extremely heavy 204.5 mm in 24 hours; a cold wave on the plains at a minimum of 4 °C or below, severe at 2 °C. Live, the app reads the heaviest 24-hour rainfall and the lowest minimum from yesterday to three days ahead.

Thresholds are in `app/surge_engine.py`. The engine plans against the worse of today and the 72-hour forecast.

**What the evidence says, and where our numbers stand:**

| Evidence | Finding | Our rule |
|---|---|---|
| Yadav et al. 2021, *Environ Sci Pollut Res* ([doi](https://doi.org/10.1007/s11356-021-13600-7)), AIIMS Delhi | Children's respiratory ER visits **+21%** on moderate and **+29%** on high-pollution days | Our top AQI bands (×1.62, ×1.90) are **higher** than this |
| Zheng et al. 2015, *PLoS ONE* ([doi](https://doi.org/10.1371/journal.pone.0138146)), meta-analysis of 37 studies | Asthma ER visits and admissions **+2.3% per 10 µg/m³ PM2.5**; effects strongest at lag ≥ 2 days | Supports the direction and the 1–3 day lag |
| Kawano et al. 2026, *npj Clean Air* ([link](https://www.nature.com/articles/s44407-026-00053-w)), 1.1 M ambulance dispatches in India | **+3.8%** same-day pediatric dispatches per 10 µg/m³, still raised over 7 days | Supports a same-day rise that lasts about a week |
| Azhar et al. 2014, *PLoS ONE* ([doi](https://doi.org/10.1371/journal.pone.0091831)), Ahmedabad 2010 heatwave | Deaths **×1.76–2.12** in the hottest week (46.8 °C) | Our ×2.10 above 44 °C matches deaths, not ORS demand; no study measures ORS demand directly |
| Bush et al. 2014, *EHP* ([doi](https://doi.org/10.1289/ehp.1306807)), Chennai | Gut-illness admissions **×1.60** in the 15 days after very heavy rain (×2.72 in under-fives), peaking days 6–15 | Basis for ORS ×1.5 after heavy rain |
| Hashizume et al. 2008, *J Water Health* ([doi](https://doi.org/10.2166/wh.2008.062)), Dhaka 1998 flood | Non-cholera diarrhoea visits **about ×2** during the flood | Basis for ORS ×2.0 in extremely heavy rain / real flooding |
| Kraay et al. 2020, *EHP* ([doi](https://doi.org/10.1289/EHP6181)), meta-analysis | Diarrhoea after floods ×1.23–1.56; strongest 4 days to 1 week after | Supports the size and the lag |
| Kakarla et al. 2019, *Epidemiol Infect* ([doi](https://doi.org/10.1017/S0950268819000608)), India IDSP | Dengue risk peaks **9–20 weeks** after heavy rain | Not modelled yet: our flood multipliers cover the acute phase only |
| Feng et al. 2023, *Sci Total Environ* ([doi](https://doi.org/10.1016/j.scitotenv.2022.160726)); Wu et al. 2024, *Environ Res* ([doi](https://doi.org/10.1016/j.envres.2023.117958)) | Respiratory admissions **×1.23** on cold-spell days; pneumonia up to **×1.69** at the peak | Basis for antibiotics ×1.25 / ×1.5 — **both studies are from China; no Indian study of cold spells and illness visits exists** |

**In short:** the direction and timing are supported; the top smog multipliers are set above what Delhi ER data shows, the heat multipliers are based on mortality, not medicine use, and the cold-wave numbers come from Chinese data. No study measures medicine use directly, so every multiplier assumes use rises in step with cases. They are planning assumptions (erring toward warning early), to be calibrated against real consumption in a pilot. The 85% / 80% / 70% shares for amoxicillin and paracetamol are design assumptions with no direct source.

</details>

<details>
<summary><b>🔌 API reference</b></summary>

<br>

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/api/environmental?region=` | Live (or scenario) air quality, weather and surge multipliers |
| `GET` | `/api/risks?region=` | Days of cover and stockout risk for every clinic and medicine |
| `GET` | `/api/recommendations?region=` | Proposed transfers waiting for approval |
| `POST` | `/api/agents/run-resilience-pipeline` | Run the five agents for one clinic (Gemini function calling + allocator) |
| `POST` | `/api/voice-intake/transcribe` | Gemini speech-to-text for a 16 kHz WAV voice note |
| `POST` | `/api/voice-intake` | Parse a stock report into a draft update |
| `POST` | `/api/approve-transfer` | CMO approval: reserves stock, issues the dispatch note |
| `POST` | `/api/cmo/chat` | Ask a question; answered from the system's own figures |
| `POST` | `/api/cmo/speak` | Read an answer aloud (Gemini text-to-speech, returns WAV) |
| `POST` | `/api/vision/verify-shelf-photo` | Count stock in a shelf photo and compare with the register |
| `GET` | `/api/audit-log/verify` | Walk the SHA-256 hash chain from the first entry |
| `GET` | `/api/system/capabilities` | What is live, what is sample data, which AI providers are set |
| `GET` | `/api/impact/value?region=` | Rupees and clinic-days your approved transfers returned, with assumptions |
| `POST` | `/api/demo/reset` | Reset your own sandbox (other visitors are unaffected) |
| `GET` | `/api/health` | Health check |

Region-scoped endpoints take `?region=indore|lucknow|bhubaneswar`; an unknown region is a `400`, never a silent fallback. The audit log is per region (`/api/audit-log?region=`).

Clinic workflow (stock actions, dispatch, receipt, reconciliation) lives under `/api/clinic/{facility_id}/…` and `/api/transfer/…`.

</details>

<details>
<summary><b>💻 Run it locally</b></summary>

<br>

```bash
git clone https://github.com/Ritesh-Root/aarogya-vayu-2036.git
cd aarogya-vayu-2036
cp .env.example .env          # add GEMINI_API_KEY (free at https://aistudio.google.com/)

uv sync                       # or: python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
uv run pytest -q              # 143 tests; no API keys needed (AI calls fall back offline)
AV_SANDBOX=1 DEFAULT_REGION=indore uv run uvicorn app.main:app --port 8000
```

Open <http://localhost:8000>. Without a Gemini key the app still runs: voice reports use the rule-based parser and the CMO answers come from a template.

> `AV_SANDBOX=1` gives each browser its own in-memory copy of the demo (as the live app does). The older tests write to `data/*.json`. Run `git checkout -- data` afterwards to restore the demo dataset, and don't run two test sessions at once.

</details>

<details>
<summary><b>🗂️ Project structure</b></summary>

<br>

```
app/
  main.py                FastAPI routes, rate limits, approval flow
  regions.py             The three regions: districts, centroid, donor radius, state code (one source of truth)
  sandbox.py             Per-visitor demo sandbox (cookie session, in-memory, capped and expiring)
  naqi.py                India National AQI (CPCB) from PM2.5 / PM10
  impact_value.py        Rupees-saved panel: prices, assumptions
  agent_orchestrator.py  The five-agent pipeline and Gemini function calling
  optimizer.py           Deterministic transfer allocator (35/50 km, 14-day reserve, FEFO)
  surge_engine.py        Weather → demand multipliers → days of cover
  telemetry_service.py   Open-Meteo + Copernicus CAMS live feed
  speech_service.py      Gemini speech-to-text and text-to-speech
  voice_service.py       Stock-report parsing and drug-list matching
  vision_service.py      Gemini shelf-photo reading
  llm.py                 Gemini first, Claude Haiku fallback, time budgets
  audit_ledger.py        SHA-256 hash-chained audit log
static/                  Single-page app (Tailwind, Leaflet, Lucide)
data/                    Facilities, sample inventory and medicines (three regions; Jan Aushadhi prices)
tests/                   143 tests: allocator invariants, API, scenarios, sandbox, NAQI, Indore, clinic workflow
scripts/smoke_ui.cjs     Playwright UI smoke test (Indore heatwave -> approve -> MP challan; second visitor untouched)
scripts/simulate_impact.py  Before/after simulation (writes docs/impact.svg and docs/impact.json)
```

</details>

---

## 💰 What it costs to run

A rough estimate for one district of 20 clinics, at Google's published Gemini API prices (checked 25 Oct 2026):

| Use per month | Assumed size | Cost |
|---|---|--:|
| 600 voice reports (transcribe + read) | ~20 s audio, then ~2k tokens in, ~0.3k out | ~$2.10 |
| 600 transfer checks (Gemini tool call) | ~3.5k tokens in, ~0.4k out | ~$2.50 |
| 300 CMO questions | ~6k tokens in, ~1.5k out (two languages) | ~$3.00 |
| 300 read-alouds (Gemini text-to-speech) | ~30 s audio each (25 tokens/s) | ~$2.00 |
| 80 shelf-photo checks | one image, short answer | ~$0.20 |
| **Total** | | **≈ $10 a month (under ₹1,000)** |

<sub>gemini-3.8-flash: $0.75 / 1M input, $3.75 / 1M output; gemini-3.8-flash-tts: $9 / 1M audio output ([pricing page](https://ai.google.dev/gemini-api/docs/pricing)). Google has announced these 3.8 prices double from 1 Jan 2027 (≈ $20 a month). Token sizes are our estimates, not measured; Gemini's thinking tokens are billed as output and could raise the total. The demo runs on one always-on Google Cloud Run instance; a pilot would add a shared, authenticated database. A global daily cap on AI calls (`AI_DAILY_CALL_BUDGET`) bounds the demo's spend.</sub>

---

## 🛡️ Safety and privacy

- **A person approves every transfer.** The AI proposes; the district CMO decides.
- **No patient data.** Only facility stock counts and batch codes (DPDP Act 2023).
- **Tamper-evident log.** Every report, approval and dispatch is SHA-256 hash-chained; editing a past entry breaks verification. Entries are not yet digitally signed, so the log proves tampering, not authorship.
- **Overlay, not a replacement.** Designed to read from e-Aushadhi / DVDMS exports (in MP, the MPPHSCL e-Aushadhi system) and send proposals back, with no new hardware.
- **Demo sandbox.** Roles are simulated and each visitor's data is a private in-memory copy that expires after a day. A real deployment would use one shared store behind real login.

## 🗺️ Roadmap

| Next | Why |
|---|---|
| Pilot in the Indore division on a read-only MP e-Aushadhi (MPPHSCL) export | Replace sample inventory with real stock, starting with Jhabua, Alirajpur and Barwani |
| Shared, authenticated store (Firestore) and real login with role-based signing | Today's demo keeps each visitor's data in memory |
| All 55 MP districts | One district health office per subscription |
| Dengue and malaria after the monsoon | Vector-borne fevers peak 1–3 months after heavy rain; floods currently cover the acute diarrhoea phase only |
| Road distance and 108/102 ambulance return trips | More realistic transport |
| Learned demand forecast | Once a pilot provides real consumption history |
| Offline voice and SMS alerts | Clinics with poor connectivity |

---

<div align="center">

Built by **Ritesh Kumar Mahato** for **BUILD 2036**, the official hackathon of the TiE Global Summit 2026, Indore<br>
<sub>Earlier version built for Google's <i>Build with AI: Code for Communities 2.0</i> (Top 10)</sub>

<sub>Air quality: <a href="https://open-meteo.com/">Open-Meteo</a> and <a href="https://atmosphere.copernicus.eu/">Copernicus CAMS</a> · Map: <a href="https://leafletjs.com/">Leaflet</a> and © OpenStreetMap contributors</sub>

</div>

# Aarogya-Vāyu 2036: design

Date: 2026-11-26. Entry for BUILD 2036 (TiE Global Summit 2026 / Hack2skill), **Health, Longevity & Biotechnology** track.
Submission closes **Mon 30 Nov 2026**. Screening 1–2 Dec, Top 10 announced 5 Dec, in-person pitch in Indore 14 Dec.
This file moves into the new repo at `docs/superpowers/specs/` once the repo exists.

## Intent and why

The user wants to win BUILD 2036. Getting into the Top 10 is the first gate. Hack2skill screens the working prototype, repo, demo video and deck. After that, a TiE jury of founders and investors, sitting in Indore, picks the finalists and winners.

The project is Aarogya-Vāyu (github.com/Ritesh-Root/aarogya-vayu, Top 10 at Google Code for Communities 2.0). It moves medicine between rural clinics before a climate surge (smog, heat, flood, cold) empties their shelves. Live air and weather data set demand multipliers. Gemini handles voice, photos and Q&A, and calls a deterministic transfer allocator. A doctor approves every transfer, and every step goes into a hash-chained audit log.

The upgrade has two aims:
- Make the project **matter to an Indore jury**: an Indore-division MP region and an MP heatwave scenario.
- Make it **hold up when a judge pokes it**: fix what an audit on 2026-11-26 found.

## Goals

1. **New public repo `aarogya-vayu-2036`.** It's a copy of the existing repo with its history kept. The old repo and the old Vercel app stay untouched as the Google contest saw them.
2. **Fix the audit findings that a judge or a stranger could trigger:**
   - Unauthenticated writes accept absurd values. `PHYSICAL_COUNT` = 1e12 and AQI = -99999 both return 200. Fix: add bounds and validation on every write endpoint, and a **Reset demo** action.
   - State is lost or split across serverless instances. A transfer approved on one instance disappears on the next request, and the audit log resets.
   - The AQI scale is wrong. Telemetry gives US AQI, but the surge bands use India's NAQI. Fix: compute the **Indian NAQI from PM2.5/PM10 using CPCB breakpoints**, and make the scenario presets consistent pairs.
   - An audit entry is written before the change it records is saved. Fix: record only after the commit succeeds.
   - Optimizer bugs:
     - The fallback batch can be smaller than the transfer quantity.
     - The unmet-demand text always says "0 of N donors".
     - The donor filter uses the earliest batch's expiry, so one bad batch excludes a donor with good stock.
   - A voice report naming an unknown facility silently becomes PHC Kakori. Fix: ask instead.
   - Switching region changes it for everyone and writes an audit entry on every click. Fix: make region per visitor, like Conditions already is.
   - Paid AI calls have no global daily budget. Fix: add a global daily cap and fall back to the rule-based path when it's hit.
   - `pyproject.toml` lists packages the code never imports (Vertex, Speech, Vision, SciPy, NumPy). Fix: remove them so the repo matches the pitch.
   - `/api/health` returns 404. Fix: add the route.
3. **A third region: Indore division, Madhya Pradesh.**
   - **About 20 facilities** in Indore, Dhar, Jhabua, Alirajpur and Barwani: district hospitals, CHCs and PHCs.
     - Use real facility names from government HMIS lists where available, e.g. DH Jhabua, CHC Meghnagar, CHC Madrani, PHC Bamniya (Petlawad), CHC Thandla, CHC Petlawad, CHC Jobat, CHC Sendhwa, CHC Rajpur, CHC Sardarpur, CHC Badnawar, CHC Kukshi, CHC Mhow, CHC Sanwer, CHC Depalpur.
     - Stock stays sample data, labelled as such.
     - Facilities are grouped by district so that donors are within reach.
   - **Donor radius becomes a per-region setting.** MP districts are large: Indore to Jhabua is about 150 km. Lucknow and Odisha keep 35 km. The MP value is the builder's call (around 50 km), chosen so the demo produces real transfers inside districts.
   - **MP heatwave scenario.** Max temperature around 46 °C, using IMD plains thresholds (heatwave ≥ 45 °C, severe ≥ 47 °C). ORS, IV fluids and fever medicine surge; the existing heat multipliers apply.
   - **Live data.** The live "today" mode works for Indore using Open-Meteo at an Indore-division centroid.
   - **State labels.** Challan state code `MP`, Hindi UI, MP vehicle-plate placeholder, a region button, and MP news/directives where the code has them.
   - **No silent fallback.** Every place that hard-codes two regions is fixed. Per the audit, that's main.py, storage.py, domain.py, telemetry_service.py, news_service.py, agent_orchestrator.py, voice_service.py, static/app.js, static/index.html and the scripts. An unknown region raises an error instead of silently using Lucknow's data.
   - **Impact simulation.** `scripts/simulate_impact.py` gets an MP heatwave run, and its number goes on the impact slide.
4. **A rupees-saved panel for the district officer.** Per region, it shows:
   - the value of near-expiry stock moved instead of wasted
   - clinic-days of stockout avoided
   - transfers approved
   - running cost per month

   Unit prices come from a published source (e.g. MP e-Aushadhi rate contracts or Jan Aushadhi MRPs). Every figure carries its source or is labelled as an assumption.
5. **Deployment that keeps state across visits.** See Approaches.
6. **Submission materials:**
   - New demo video, about 2–3 minutes, showing the Indore flow, with narration.
   - Canva deck, about 10 slides (outline already approved):
     - Real photographs, no vector art.
     - Light palette: cream `#FDF7F2`, terracotta `#C95836`/`#DE6B48`, forest green `#2F6B52`, amber `#FFF1DB`, ink `#2E221D`.
     - MP is shown as built only for what is actually built.
   - Form text: prototype brief and tech stack, each ≤ 1024 characters.
   - README and pitch kit updated for BUILD 2036.
   - Everything final copied to `~/Downloads/build2036-submission/`.

## Non-goals

- A rewrite or a stack change. It stays Python 3.12, FastAPI, vanilla JS and Gemini 3.8 Flash.
- Real e-Aushadhi / DVDMS integration. That's roadmap only; MP's system is e-Aushadhi, run by MPPHSCL.
- Real login and role-based signing. That's roadmap. The demo keeps simulated roles but becomes vandal-resistant.
- A trained demand model. The demand engine stays transparent rules.
- Bhili or other tribal-language voice input.

## Anti-goals (failure even if it works)

- Any claim in the deck, README, form or video that the code doesn't back up. The old pitch already had to retract Earth Engine, Vertex and SciPy claims, and judges check.
- A live demo that a judge finds broken, empty or vandalised.
- Breaking Lucknow or Odisha while adding Indore. All 55 existing tests must stay green.

## Constraints

- **Time:** four days, with Monday as a buffer.
  - Thu: repo + fixes
  - Fri: Indore region
  - Sat: rupees panel + deploy + tests
  - Sun: video + deck + form
  - Mon: buffer and submit
- **Cut order if late:**
  1. MP news curation
  2. MP voice samples
  3. Rupees panel reduced to two figures
  4. Never cut the fixes or the region itself
- **GCP:** the billing account is capped at 5 projects, all in use. Any GCP resource must go in the existing project `ai-prompt-493423` (asia-south1).
- **Canva:**
  - The sign-in needs refreshing via `/mcp`.
  - AI generation quota may be used up until 2026-12-10.
  - Fallback: build a `.pptx` with the same photos and palette.
- **Commits:** end every commit with the Co-Authored-By line the session specifies.

## Approaches (state that survives serverless)

| | Approach | Trade-off |
|---|---|---|
| A | Keep Vercel, move state to **Firestore** in `ai-prompt-493423` (the existing backend, fixed to scope by region, plus the missing dependency). | Durable and consistent. Needs a GCP service-account key stored in Vercel and more code changes. |
| B | Move the app to **Cloud Run** in `ai-prompt-493423` with **one always-on instance** (`min=max=1`) and keep the JSON files. | Smallest code change; one instance means one consistent state. A restart still resets to the seed data, which is fine for a demo with a Reset button. Costs a few dollars over three weeks. |
| C | Keep Vercel as it is and only add a Reset button. | Doesn't fix approvals disappearing between requests. Rejected. |

**Pick: B (my call).** It fixes the "judge approves, the transfer vanishes" bug with the least risk inside four days, and SmogWise already deploys to the same project. A is the right production answer and goes on the roadmap slide.

## Calls made after the builder check (my calls, user may override)

1. **Every visitor gets a private sandbox.** Stock, approvals, consignments and the audit log are keyed by a session id (a cookie set on first visit). Each session starts from that region's seed data. This replaces "shared state + Reset button":
   - One judge's clicks can't change what another judge sees.
   - Vandalism only affects the vandal's own copy.
   - "Reset demo" resets only your own sandbox.

   Sessions are held in memory on the single Cloud Run instance, expire after 24 h idle, and are capped in number (oldest evicted). Input bounds are still added. The README says plainly that this is a per-visitor demo sandbox, and that a real deployment would use one shared, authenticated store (roadmap: Firestore).
2. **Tests that assert the old, wrong behaviour get updated, not kept.** Examples: the US-AQI smog multiplier assertions and the optimizer and unknown-facility cases. Each such change is listed in the commit message. Every other existing test must pass unchanged.
3. **The Claude Haiku 5.5 text fallback stays.** It's already in the README. The pitch and deck say "Gemini 3.8 Flash, with Claude Haiku 5.5 as a fallback". Both count toward the global daily AI budget. On Cloud Run, Gemini runs through **Vertex AI using the service account** in `ai-prompt-493423`, as SmogWise does, so no API key needs copying. The builder must confirm that the live Gemini path works on the deployed URL before recording the video.
4. **"Running cost per month" means the projected production cost per 20-clinic district**, from published Gemini prices and stated assumptions (the existing estimate is about $10 / under ₹1,000). It is labelled as an estimate, and the same number appears on deck slide 8.
5. **Public URL:** the Cloud Run `*.run.app` URL, used in the README, form and deck. The old Vercel app stays as it is for the old repo. The new repo gets no Vercel deploy.
6. **Video narration:** generated with ElevenLabs, as for SmogWise. The user's account and key are already set up. The user can record their own voice instead if they prefer.

## Decided by the user

- Project: Aarogya-Vāyu. Track: Health. Copy and upgrade in a new repo, not a rewrite.
- Add the Indore/MP region. Fix the issues the earlier version missed.
- Deck: Canva, real photos, light palette matching the app, about 10 slides. The slide 8 business model (district health office pays per district) is the user's to correct.

## Left to the builder

- Exact MP donor radius, facility coordinates and stock levels, within the goals above.
- How the region becomes per-visitor: query parameter or header.
- Global AI budget numbers.
- Test structure for the new cases.

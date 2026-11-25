# Aarogya-Vāyu 2036 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Aarogya-Vāyu in a new repo for BUILD 2036. The upgrade fixes the audit findings, adds an Indore-division (MP) region, adds a rupees-saved panel and a per-visitor demo sandbox, deploys to a single always-on Cloud Run instance, and produces the video, deck and form text by Mon 30 Nov 2026.

**Architecture:**
- **One region registry.** A new `app/regions.py` replaces every hard-coded two-region branch.
- **Per-visitor sandbox.** A cookie session id lives in a contextvar. `StorageManager` and `AuditLedger` read it, so all existing call sites become session-scoped without changing their signatures.
- **Indian AQI.** A new `app/naqi.py` computes India's NAQI from PM2.5/PM10. The surge bands already assume that scale.
- **Hosting.** One Cloud Run instance (`min=max=1`) holds the sessions in memory.

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, vanilla JS (`static/app.js`), google-genai (Gemini 3.8 Flash; Vertex mode on Cloud Run), anthropic (fallback), pytest, Docker, gcloud, Playwright (UI smoke + video), ElevenLabs (narration), Canva MCP (deck).

**Spec:** `docs/superpowers/specs/2026-11-26-aarogya-vayu-2036-design.md` (starts at `/Users/ritesh/code/build2036/`; Task 0 moves it into the repo).

## Global Constraints

- **Repo:** new public `Ritesh-Root/aarogya-vayu-2036`, a full-history copy of `Ritesh-Root/aarogya-vayu`. Never push to or redeploy the old repo or the old Vercel app.
- **Stack:** no stack change. Python 3.12 / FastAPI / vanilla JS / Gemini 3.8 Flash with the Claude Haiku 5.5 fallback.
- **Tests:** all existing tests stay green. The only tests that may change are ones asserting old, wrong behaviour. Each such change is named in the commit message.
- **Regions:** `lucknow`, `bhubaneswar`, `indore`. Unknown region → HTTP 400 / `UnknownRegionError`. Never a silent fallback.
- **GCP:** project `ai-prompt-493423`, region `asia-south1`. No new GCP projects (the billing cap is reached). Project-level IAM changes must be run by the user with `!`.
- **Copy:** every number in the README, deck, form and video must be backed by code or a cited source. Sample data and simulations are labelled as such.
- **Commits:** end each one with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Stage files by path, never `git add -A`.
- **Deliverables:** final video, deck (PPTX + PDF) and form text are copied to `~/Downloads/build2036-submission/`.

## Review Focus

1. **Two visitors at once.** Visitor A approves a transfer. Visitor B, with a different cookie, must still see the seed state and A's ledger entries must not appear for B. Test owner: Task 2.
2. **A request with no `region` parameter, or an unknown one, on a region-scoped endpoint.** No region → the default region. Unknown region → 400. It must never be Lucknow's data under another region's name. Test owner: Task 1.
3. **Session flood.** 2,000 new cookies must not grow memory without bound: the session count is capped at `SANDBOX_MAX_SESSIONS` and the least recently used are evicted. Test owner: Task 2.
4. **Container restart mid-demo.** An existing cookie with no session in memory is re-seeded silently, with no 500. Test owner: Task 2.
5. **Missing or extreme air data.** NAQI with `pm10=None`, PM2.5 above 380, and negative values must not raise. Indore telemetry outage → Indore fallback values, not Bhubaneswar's. Test owners: Tasks 4 and 7.

---

### Task 0: New repo, baseline green

**Files:**
- Create: `~/code/aarogya-vayu-2036/` (full clone)
- Create: `docs/superpowers/specs/2026-11-26-aarogya-vayu-2036-design.md`, `docs/superpowers/plans/2026-11-26-aarogya-vayu-2036-plan.md` (moved from `~/code/build2036/`)

- [ ] **Step 1:** `git clone https://github.com/Ritesh-Root/aarogya-vayu.git ~/code/aarogya-vayu-2036`. Full history, not shallow.
- [ ] **Step 2:** Create the public GitHub repo `aarogya-vayu-2036`, set it as `origin`, and push `main`. If the permission classifier blocks `gh repo create`, ask the user to run `! gh repo create Ritesh-Root/aarogya-vayu-2036 --public` and then push.
- [ ] **Step 3:** `uv venv .venv && uv pip install -r requirements.txt pytest`. Then `pytest -q`. Expected: `55 passed`.
- [ ] **Step 4:** Move the spec and the plan into `docs/superpowers/`. Commit as `docs: BUILD 2036 design and plan`.

### Task 1: Region registry, no silent fallback

**Files:**
- Create: `app/regions.py`
- Modify: `app/storage.py:66-81`, `app/domain.py:95-120`, `app/telemetry_service.py:14-30,104,218-222`, `app/main.py:61-79,92-155,160-191,203-226,376-405`, `app/agent_orchestrator.py:341-344,510`, `app/news_service.py:208-215,334`, `app/voice_service.py:128,199-201,265`, `app/audit_ledger.py:31`, `app/models.py:83`
- Test: `tests/test_regions.py`

**Interfaces:**
- Produces:
  - `class UnknownRegionError(ValueError)`
  - `REGIONS: dict[str, RegionConfig]`
  - `get_region(region_id: str | None) -> RegionConfig`. `None` → `DEFAULT_REGION`; an unknown id raises `UnknownRegionError`.
  - `region_for_district(district: str) -> str | None`
  - `RegionConfig` is a frozen dataclass with these fields:
    - `id`, `label`, `state_code`, `districts: tuple[str, ...]`
    - `centroid: tuple[float, float]`, `heatwave_threshold_c: float`, `max_distance_km: float`
    - `default_facility_id`, `facilities_file`, `inventory_file`, `consignments_file`, `idempotency_file`
    - `corridor_name`, `map_center`, `map_zoom`, `polygon`, `initial_env: dict`
  - `DEFAULT_REGION = os.getenv("DEFAULT_REGION", "bhubaneswar")` (`"lucknow"` under pytest, as today).
- `main.py` registers an exception handler that turns `UnknownRegionError` into a 400 with `{"detail": "Unknown region: <id>"}`.

- [ ] **Step 1: Write failing tests** in `tests/test_regions.py`:
  - `test_unknown_region_raises`: `get_region("mars")` raises `UnknownRegionError`.
  - `test_api_unknown_region_400`: `GET /api/risks?region=mars` returns 400.
  - `test_storage_paths_per_region`: `StorageManager._get_region_paths("bhubaneswar")[0].name == "inventory_bhubaneswar.json"`, the `lucknow` path is `inventory.json`, and `"mars"` raises.
  - `test_facility_region_by_district`: for every facility in `facilities.json` and `facilities_bhubaneswar.json`, `domain_service.get_region_for_facility(id)` equals its file's region.
  - `test_state_code`: `_state_code` gives `UP` for a Lucknow facility and `OD` for a Bhubaneswar facility.
  - `test_optimizer_radius_per_region`: Lucknow and Bhubaneswar use 35.0.
- [ ] **Step 2:** `pytest tests/test_regions.py -v`. Expected: FAIL (`app.regions` doesn't exist).
- [ ] **Step 3:** Implement `app/regions.py`, filling the Lucknow and Bhubaneswar entries from today's `REGIONS_CONFIG`, `COORDINATES` and the storage paths. Then replace every hard-coded branch listed under Files with registry lookups:
  - `domain.get_region_for_facility` uses `region_for_district`. The substring heuristic goes, and the final fallback raises `UnknownRegionError` instead of returning the active region.
  - The optimizer takes `max_distance_km` from the region of the recipient facility.
- [ ] **Step 4:** `pytest -q`. Expected: all pass (55 + new).
- [ ] **Step 5:** Commit: `refactor: single region registry; unknown regions are rejected`.

### Task 2: Per-visitor sandbox and audit rollback

**Files:**
- Create: `app/sandbox.py`
- Modify: `app/storage.py` (load/commit/execute_in_transaction), `app/audit_ledger.py`, `app/main.py` (middleware, `/api/audit-log*` take `region`, new `POST /api/demo/reset`, `/api/region/switch` no longer mutates globals or writes audit entries)
- Test: `tests/test_sandbox.py`

**Interfaces:**
- Produces (`app/sandbox.py`):
  - `current_session: ContextVar[str]`, default `"shared"`
  - `current_region: ContextVar[str | None]`
  - `SESSION_COOKIE = "av_session"`
  - `SANDBOX_ENABLED = os.getenv("AV_SANDBOX", "0") == "1"`
  - `SANDBOX_MAX_SESSIONS = int(os.getenv("SANDBOX_MAX_SESSIONS", "500"))`
  - `SANDBOX_TTL_S = 86400`
  - `class SessionStore` with:
    - `get(session_id: str, region: str, seed: Callable[[], dict]) -> dict`: LRU ordering, TTL expiry, cap eviction.
    - `reset(session_id: str) -> None`
    - `__len__`
- Produces (`AuditLedger`):
  - `entries` becomes a property scoped to `(current_session, current_region)` when sandboxed. When not sandboxed, it keeps today's file behaviour.
  - Each chain gets its own GENESIS entry.
  - `rollback_to(length: int) -> None` truncates the current chain.
- `StorageManager`: when `SANDBOX_ENABLED`, load and commit read and write the session's in-memory copy (deep-copied, seeded from the bundled JSON) and never touch disk. `execute_in_transaction(mutation_fn, region)` does three things:
  1. sets `current_region`,
  2. records `n = len(ledger.entries)`,
  3. calls `ledger.rollback_to(n)` if the mutation or the commit raises.

  This fixes the audit-before-commit finding. To make it possible, `StorageManager` gets the ledger injected: `storage.attach_ledger(ledger)`.
- Middleware: if the request has no valid `av_session` cookie (uuid4 hex), it sets one: `HttpOnly`, `SameSite=Lax`, `Secure` when the request is https, max-age 86400.

- [ ] **Step 1: Write failing tests** in `tests/test_sandbox.py`. Use `monkeypatch.setenv("AV_SANDBOX","1")` and reload, or construct with a `sandbox=True` kwarg; the builder picks one.
  - `test_two_visitors_isolated`: client A approves the first Lucknow smog recommendation. Client B, with a fresh cookie jar, gets a `/api/clinic/PHC-LKO-01/desk` whose stock equals the seed. B's `/api/audit-log?region=lucknow` has exactly 1 entry (GENESIS).
  - `test_reset_only_mine`: A makes a stock action and B makes one. A calls `POST /api/demo/reset`. A is back to seed; B keeps its change.
  - `test_session_cap`: with `SANDBOX_MAX_SESSIONS=50`, 200 distinct cookies leave `len(store) <= 50`.
  - `test_unknown_session_reseeds`: a request with cookie `av_session=<valid uuid never seen>` returns 200 with seed data.
  - `test_rollback_on_commit_failure`: monkeypatch `commit_transaction` to raise `StorageError`. A stock action returns 5xx, and the ledger length is unchanged.
  - `test_region_switch_has_no_side_effects`: two `POST /api/region/switch` calls add no audit entries and don't change another client's region.
  - `test_ledger_per_region_verifies`: after actions in two regions, `/api/audit-log/verify?region=X` is valid for each.
- [ ] **Step 2:** `pytest tests/test_sandbox.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement as specified under Interfaces. The frontend changes (sending `region`, the reset button) are in Task 8.
- [ ] **Step 4:** `pytest -q`. Expected: all pass. Existing tests run with `AV_SANDBOX` unset, so file behaviour is unchanged.
- [ ] **Step 5:** Commit: `feat: per-visitor demo sandbox; audit entries roll back with failed commits`.

### Task 3: Input bounds on every write

**Files:**
- Modify: `app/models.py` (`StockActionRequest`, `EnvironmentalReading`, `ApprovalRequest`, dispatch/receive/cancel request models, `VoiceIntakeRequest`)
- Test: `tests/test_bounds.py`

**Interfaces:** pydantic `Field` constraints, so a violation is a 422:
- `quantity`: `ge=0, le=100_000`
- `aqi`: `0–500`
- `pm25`: `0–1500`
- `pm10`: `0–2000`
- `temperature_c`: `-30–60`
- `humidity`: `0–100`
- `rainfall_mm`: `0–2000`
- string ids: `max_length=64`, pattern `^[A-Za-z0-9_-]+$`

- [ ] **Step 1: Write failing tests:**
  - `test_physical_count_huge_rejected`: `quantity=10**12` returns 422.
  - `test_env_negative_aqi_rejected`: `aqi=-99999` returns 422.
  - `test_env_absurd_temp_rejected`: `temperature_c=1e9` returns 422.
  - `test_valid_stock_action_still_200`.
- [ ] **Step 2:** Run. Expected: FAIL (200 today).
- [ ] **Step 3:** Add the constraints. Check that the scenario presets and the seed data are inside the bounds.
- [ ] **Step 4:** `pytest -q`. Expected: all pass.
- [ ] **Step 5:** Commit: `fix: bound all write inputs (audit finding 1)`.

### Task 4: Indian NAQI

**Files:**
- Create: `app/naqi.py`
- Modify:
  - `app/telemetry_service.py`: request `pm10` hourly; compute `aqi` and `forecast_peak_aqi_72h` with `naqi_from_pm`; keep `us_aqi` only as a reference field. `smog_episode` stays "forecast AQI peak >= 200", now on NAQI.
  - `app/main.py:261-290`: preset `aqi` derived from its `pm25`/`pm10`.
  - `static/` label: "AQI (India NAQI)".
- Test: `tests/test_naqi.py`; update `tests/test_aarogya_vayu.py:916-940`.

**Interfaces:**
- Produces `naqi_from_pm(pm25: float | None, pm10: float | None) -> int`:
  - the max of the sub-indices, linear inside each band, rounded half up, clamped to `0–500`
  - a `None` input is ignored; both `None` → 0
  - negatives are treated as 0
- Produces `naqi_category(aqi: int) -> str`: `Good | Satisfactory | Moderate | Poor | Very Poor | Severe`.
- Breakpoints (CPCB, continuous form):
  - PM2.5: `0-30→0-50, 30-60→50-100, 60-90→100-200, 90-120→200-300, 120-250→300-400, 250-380→400-500`
  - PM10: `0-50→0-50, 50-100→50-100, 100-250→100-200, 250-350→200-300, 350-430→300-400, 430-510→400-500`
  - Above the top breakpoint → 500.

- [ ] **Step 1: Write failing tests:**
  - `test_band_edges`: PM2.5 values 30/60/90/120/250 → 50/100/200/300/400.
  - `test_mid_band`: `naqi_from_pm(200, None) == 362`.
  - `test_pm10_dominates`: `naqi_from_pm(20, 300) == 250`.
  - `test_missing_and_extreme`: `naqi_from_pm(None, None) == 0`, `naqi_from_pm(900, None) == 500`, `naqi_from_pm(-5, None) == 0`.
  - `test_categories`: 50 → "Good", 362 → "Very Poor", 401 → "Severe".
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement and wire into telemetry and the presets. Update the old test `test_live_telemetry_derives_forecast_peak_and_aod_anomaly` so its hourly `pm2_5`/`pm10` produce the intended NAQI peak (e.g. PM2.5 200 at h=20 → 362 → smog multiplier 1.62). Name this change in the commit.
- [ ] **Step 4:** `pytest -q`. Expected: all pass.
- [ ] **Step 5:** Commit: `fix: use India NAQI from PM2.5/PM10, not US AQI (audit finding 5; updates live-telemetry test)`.

### Task 5: Correctness fixes (optimizer, voice)

**Files:**
- Modify: `app/optimizer.py:132-140,229-240,320-330`, `app/voice_service.py:128,265`
- Test: `tests/test_correctness.py`

**Rules:**
- **Donor eligibility** is based on usable stock: batches with `days_to_expiry >= 30`. One near-expiry batch no longer disqualifies a donor whose other batches qualify.
- **Batch selection:** the transfer quantity is capped at the largest single FEFO batch that is still usable. A challan never names a batch smaller than its quantity.
- **Unmet-demand text:** reports the real count, e.g. `"{k} of {n} peer facilities could donate; {units} units still unmet"`.
- **Unknown voice facility:** a facility that can't be matched returns `needs_confirmation=True` with `facility_id=None` and a message asking which clinic. No default to `PHC-LKO-01`.

- [ ] **Step 1: Write failing tests**, using hand-built `facilities_dict` and inventory fixtures:
  - `test_donor_with_one_bad_batch_still_donates`
  - `test_challan_batch_covers_quantity`: for every recommendation in all three regions × all scenarios, the selected batch's available ≥ quantity.
  - `test_unmet_text_counts_partial_donors`
  - `test_voice_unknown_facility_asks`
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** `pytest -q`. Expected: all pass. Rerun `scripts/simulate_impact.py`. If −42%/−83% move, record the new numbers; Task 10 uses them.
- [ ] **Step 5:** Commit: `fix: optimizer batch/donor/unmet edge cases; voice asks for unknown clinic`.

### Task 6: AI budget, health route, dependency trim

**Files:**
- Modify: `app/main.py:594-612`, `app/llm.py`, `pyproject.toml`
- Test: `tests/test_budget.py`

**Interfaces:**
- `AI_DAILY_CALL_BUDGET = int(os.getenv("AI_DAILY_CALL_BUDGET", "1500"))`, a process-wide counter that resets at IST midnight.
- `consume_ai_budget() -> bool` is called inside `llm.py` before every provider call.
- When the budget is spent:
  - parse, chat and pipeline use the existing rule-based paths
  - TTS and vision return 429 with `{"detail":"Daily AI budget reached; try tomorrow"}`
- `GET /api/health` → `{"status":"ok"}`.
- `pyproject.toml`: remove `google-cloud-aiplatform`, the speech, texttospeech and vision packages, `scipy` and `numpy`, plus any other dependency `app/` doesn't import (check with grep).

- [ ] **Step 1: Write failing tests:**
  - `test_budget_exhausted_falls_back`: chat answers with `answered_by` containing "rules".
  - `test_tts_429_when_spent`
  - `test_health_ok`
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** `pytest -q && uv pip install -e . --dry-run`. Expected: all pass and dependencies resolve.
- [ ] **Step 5:** Commit: `feat: global daily AI budget, /api/health; drop unused deps`.

### Task 7: Indore-division region (backend + data)

**Files:**
- Create: `data/generate_mock_data_indore.py`, `data/facilities_indore.json`, `data/inventory_indore.json`, empty `data/consignments_indore.json` (`{}`), `data/idempotency_indore.json` (`{}`)
- Modify:
  - `app/regions.py`: the `indore` entry
  - `app/main.py`: `SCENARIO_PRESETS` for indore
  - `app/news_service.py`: MP directives, or a neutral fallback if cut
  - `app/telemetry_service.py`: the Indore fallback reading
- Test: `tests/test_indore.py`

**Values:**
- `id="indore"`, `label="Indore Division (MP)"`, `state_code="MP"`
- `districts=("Indore","Dhar","Jhabua","Alirajpur","Barwani")`
- `centroid=(22.77, 74.59)` (Jhabua, the most heat-vulnerable district)
- `heatwave_threshold_c=40.0`
- `max_distance_km=50.0`
- `default_facility_id` = the first critical clinic in the heat scenario
- **Facilities:** 20 (≈4 per district), each a DH, CHC or PHC.
  - Use real names: DH Jhabua, CHC Meghnagar, CHC Madrani, PHC Bamniya, CHC Thandla, CHC Petlawad, CHC Jobat, DH Alirajpur, DH Barwani, CHC Sendhwa, CHC Rajpur, DH Dhar, CHC Sardarpur, CHC Badnawar, CHC Kukshi, CHC Mhow, CHC Sanwer, CHC Depalpur, plus two more real PHCs.
  - Use real approximate coordinates (the builder looks them up).
  - IDs look like `CHC-JBA-01`.
- **Inventory:** generated with a fixed seed. It must include at least one critical-recipient / healthy-donor pair inside each district.
- **Heat preset:** `temperature_c=46.0`, `heatwave_alert=True`, PM2.5 70 / PM10 140 (NAQI from Task 4).
- **Live mode:** Open-Meteo at the centroid. The outage fallback is Indore's own `initial_env`.

- [ ] **Step 1: Write failing tests:**
  - `test_indore_facilities_in_districts`: 20 facilities, all in the 5 districts, and the region resolves via `region_for_district`.
  - `test_generator_deterministic`: the generator run twice gives identical JSON.
  - `test_heat_scenario_makes_transfers`: `GET /api/recommendations?region=indore&scenario=heat` returns ≥3 recommendations, all with `distance_km <= 50`.
  - `test_indore_challan_state_mp`: approving one gives a challan with state code `MP`.
  - `test_indore_outage_uses_indore_fallback`: `_get_json` raising → the reading's `district` is in Indore's districts.
  - `test_lucknow_bbs_unchanged`: existing recommendation counts for Lucknow smog and Bhubaneswar heat equal their pre-task values (snapshot them first).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement the generator, run it, and add the registry entry and presets.
- [ ] **Step 4:** `pytest -q`. Expected: all pass.
- [ ] **Step 5:** Commit: `feat: Indore-division (MP) region with heatwave scenario`.

### Task 8: Frontend: three regions, per-visitor region, reset

**Files:**
- Modify: `static/app.js` (REGIONS :31-145 built from `/api/regions`; `updateRegionButtons` :241-252 renders N buttons; `regionForFacility` :1165 uses the facility's `region` field from the API; :469, :1128-1130, :2625, :3402 `MP-09-…` placeholder, :3822; voice samples :1246-1260 add a Hindi MP sample), `static/index.html` (:308-312 region buttons container, the default labels at :409/:465/:492/:1042/:1233, a "Reset my demo" button, "AQI (India NAQI)")
- Modify: `/api/facilities` response includes `region` per facility.
- Test: `scripts/smoke_ui.mjs` (Playwright, run against a local uvicorn with `AV_SANDBOX=1`)

**Behaviour:**
- The region choice is stored in `localStorage` (wrapped in try/catch) and sent as `?region=` on every region-scoped call, including `/api/audit-log*`.
- The UI never calls `/api/region/switch` for state.

- [ ] **Step 1:** Write `scripts/smoke_ui.mjs`. It opens `/`, clicks the Indore button, picks the Heat scenario, presses Find stock on the first clinic, approves, and then asserts:
  - the challan contains "MP"
  - the audit tab shows the approval
  - a second browser context still shows Lucknow/Bhubaneswar seed data and an empty audit log
  - no console errors
- [ ] **Step 2:** Run it: `AV_SANDBOX=1 uvicorn app.main:app --port 8000 & node scripts/smoke_ui.mjs`. Expected: FAIL (no Indore button).
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the smoke script and `pytest -q`. Expected: both pass. Take screenshots of every region into `screenshots/` (`proj_indore_*.png`) for the deck.
- [ ] **Step 5:** Commit: `feat(ui): Indore region, per-visitor region and reset`.

### Task 9: Rupees-saved panel

**Files:**
- Create: `app/impact_value.py`
- Modify: `data/medicines.json` (adds `unit_price_inr`, `price_source` per medicine), `app/main.py` (`GET /api/impact/value?region=`), `static/app.js` + `index.html` (dashboard card)
- Test: `tests/test_impact_value.py`

**Interfaces:**
- Produces `region_value_summary(region: str, inventory: list[dict], consignments: dict, recommendations: list) -> dict` with keys:
  - `expiry_value_saved_inr: int`: approved transfers whose donor batch would expire before the donor could use it, × the unit price
  - `stockout_days_avoided: float`: Σ over approved transfers of `min(new_days, 7) - min(old_days, 7)`
  - `transfers_approved: int`
  - `projected_monthly_cost_inr: int`: a constant of 1000
  - `assumptions: list[str]`: each assumption states its source
- **Prices:** take unit prices from the PMBJP (Jan Aushadhi) product list or MP e-Aushadhi rate contracts. Put the URL in `price_source`. If no price can be sourced for a medicine, leave it `null`; that medicine then counts 0 rupees, and the list of unpriced medicines is returned in the output.
- **Running cost:** the ₹1,000/month figure comes from the pitch kit's Gemini-price estimate and is labelled "estimate".

- [ ] **Step 1: Write failing tests:**
  - `test_value_zero_before_any_approval`
  - `test_value_after_approval`: approve one Indore heat transfer; `transfers_approved == 1` and `stockout_days_avoided > 0`.
  - `test_unpriced_medicine_counts_zero_and_is_listed`
  - `test_endpoint_per_visitor`: another session still reads 0.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. The dashboard card shows the 4 figures plus an "i" button with the assumptions.
- [ ] **Step 4:** `pytest -q` and the smoke script. Expected: pass.
- [ ] **Step 5:** Commit: `feat: rupees-saved panel for the district officer`.

### Task 10: Impact simulation for MP; docs for BUILD 2036

**Files:**
- Modify: `scripts/simulate_impact.py:44-55,199,223` (adds an `indore` heatwave run), `docs/impact.{json,svg,png}`, `README.md`, `SUBMISSION_PITCH.md`, `/api/system/capabilities`
- Delete: `generate_deck.py` (superseded by the Canva deck), `scripts/reset_pilot_dataset.py` if it's Lucknow-only and unused, or generalise it to the registry

- [ ] **Step 1:** Run `python scripts/simulate_impact.py`. Record the 7/14/21-day figures for all three corridors.
- [ ] **Step 2:** Rewrite the README for BUILD 2036 (Health track):
  - the Indore story first (heat-vulnerable Jhabua/Alirajpur/Barwani, citing Das et al. 2026, Springer)
  - live URL = Cloud Run (filled in after Task 11)
  - the per-visitor sandbox note
  - "Gemini 3.8 Flash, with Claude Haiku 5.5 as fallback"
  - updated test count
  - NAQI
  - the roadmap: shared authenticated store (Firestore), MP e-Aushadhi (MPPHSCL) integration, real login

  Remove the Google-contest badge from the header, but keep "Top 10 at Code for Communities 2.0" as a credential line.
- [ ] **Step 3:** Check every number in the README against the code or the simulation output.
- [ ] **Step 4:** Commit: `docs: BUILD 2036 README, MP impact simulation`.

### Task 11: Deploy to Cloud Run (single instance)

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `.gcloudignore`
- Modify: `app/llm.py:81-100`: when `GOOGLE_GENAI_USE_VERTEXAI=true`, construct `genai.Client(vertexai=True, project=…, location=os.getenv("GOOGLE_CLOUD_LOCATION","global"))`; otherwise use the API key as today.
- Delete: `vercel.json`, `api/index.py` (the new repo doesn't deploy to Vercel)

**Dockerfile:** `python:3.12-slim`, `pip install -r requirements.txt`, `CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}`, with `ENV AV_SANDBOX=1`.

- [ ] **Step 1:** Run `~/google-cloud-sdk/bin/gcloud run deploy aarogya-vayu-2036 --source . --region asia-south1 --project ai-prompt-493423` with:
  - `--min-instances 1 --max-instances 1 --concurrency 80 --memory 1Gi`
  - `--service-account smogwise-runtime@ai-prompt-493423.iam.gserviceaccount.com`
  - `--set-env-vars AV_SANDBOX=1,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=ai-prompt-493423,GOOGLE_CLOUD_LOCATION=global,DEFAULT_REGION=indore`
  - `--allow-unauthenticated`

  Use the Anthropic key from Secret Manager only if one already exists; otherwise the fallback is the rule-based path.
- [ ] **Step 2:** Verify against the live URL:
  - `/api/health` returns 200.
  - `/api/cmo/chat` returns `answered_by` containing "Gemini".
  - `/api/cmo/speak` returns audio. If Vertex doesn't serve the TTS model, note it and hide the Read-aloud button rather than ship a broken one.
- [ ] **Step 3:** Run `node scripts/smoke_ui.mjs` against the live URL. Expected: pass.
- [ ] **Step 4:** Put the URL into the README. Commit `chore: Cloud Run deploy`, and push.

### Task 12: Demo video (2–3 min)

- [ ] **Step 1:** Write the script, ≤ 2:45, following the flow below. All numbers come from Tasks 9 and 10 output.
  1. Problem: Jhabua heat
  2. Live Indore air and weather
  3. Hindi voice report
  4. Find stock → Gemini calls the solver
  5. Doctor approves → challan with MP
  6. Rupees panel
  7. Audit verify
  8. Impact numbers
- [ ] **Step 2:** Record the live URL with Playwright scenes and generate ElevenLabs narration (voice Alice; key in `~/.zshrc`, never printed). Mix with ffmpeg-static, as in the SmogWise demo build. Output `aarogya-vayu-2036-demo.mp4`, 1280×720, with captions.
- [ ] **Step 3:** The user uploads it to YouTube (unlisted is fine). Put the link in the README.

### Task 13: Deck, form text, hand-off

- [ ] **Step 1: Canva deck**, about 10 slides, following the approved outline. Requirements:
  - real photographs (rural clinics, nurses, medicine shelves, heat), no vector art
  - the light palette from the spec
  - Task 8 screenshots
  - slide 7 numbers from Task 10
  - slide 8 business model: district health office pays per district, running cost under ₹1,000/month (estimate)

  If Canva AI quota or auth blocks this, build a `.pptx` with the pptx skill using the same photos and palette. Export PPTX and PDF.
- [ ] **Step 2:** Write the form text: prototype brief (≤1024 characters) and tech stack (≤1024 characters). Count the characters.
- [ ] **Step 3:** Copy the deck, video, form text and links into `~/Downloads/build2036-submission/`. Update the memory file `build2036-aarogya-vayu.md` with the URLs and status.

# GitHub Copilot instructions — Zelenza CEX (Iberdrola)

This file contains concise, actionable guidance for AI coding agents and reviewers to be productive in this repository.

## Quick start (local dev)
- Install deps: `pip install -r requirements.txt` (devcontainer available at `.devcontainer/`).
- Run the app: `streamlit run main_app.py` (the UI is a Streamlit single-process app; `streamlit run main.py` also works).

## Big picture
- Single-process Streamlit web app with clear separation:
  - UI / orchestration: `main.py`, `main_app.py`, `ui_components.py`.
  - User facing logic: `user_functions.py` (calculators, PVD UI, invoice models).
  - Admin UI: `admin_functions.py`.
  - Business logic (calculations): `calculation.py`, `calculation_extended.py`.
  - Queue/timers domain: `pvd_system.py` (core PVD queue/timer logic).
  - Persistence and migrations: `database.py` (loads/saves `data/*.json`/csv and writes automatic backups to `data_backup/`).
  - Helpers: `utils.py`, `notifications.py`, `config.py` (defaults/constants).

## Data & persistence (important)
- Canonical data folder: `data/` (CSV and JSON). Backups copied to `data_backup/` automatically by `database.inicializar_datos()`.
- Key files and formats to respect:
  - `data/precios_luz.csv` expected columns: `plan,precio_original_kwh,con_pi_kwh,sin_pi_kwh,punta,valle,total_potencia,activo,umbral_especial_plus,comunidades_autonomas`
  - `data/planes_gas.json` contains plan dicts (see `config.PLANES_GAS_ESTRUCTURA`).
  - `data/cola_pvd.json` is an array of pause objects; typical keys: `id`, `usuario_id`, `usuario_nombre`, `duracion_elegida`, `estado` (ESPERANDO|EN_CURSO|COMPLETADO), `timestamp_solicitud`, `timestamp_inicio`, `timestamp_fin`, `confirmado`, `notificado_en`.

Example snippet from `data/cola_pvd.json`:
```
{ "id": "5f32b4ad", "usuario_id": "0001", "duracion_elegida": "corta", "estado": "ESPERANDO", "timestamp_solicitud": "2025-12-21T16:05:42.221388+01:00", ... }
```

- Always use `database.cargar_*` / `database.guardar_*` helpers to read/write data so backups + migrations are preserved.

## Time and timezone rules
- The system consistently uses Europe/Madrid timezone (pytz) and ISO timestamps. Use `utils.obtener_hora_madrid()` / `utils.formatear_hora_madrid()` when working with times to avoid TZ bugs.
- When adding timestamps, prefer `.isoformat()` with timezone awareness.

## PVD (Pause Visual) system specifics
- Core queue + timer behaviors live in `pvd_system.py` and are referenced by `user_functions.py` and `main_app.py`.
- There is a global `temporizador_pvd` instance exported by `pvd_system.py` used to start/cancel per-user timers.
- `pvd_system.iniciar_siguiente_en_cola()` enforces confirmation flow: a user must be `confirmado` to go from `ESPERANDO`→`EN_CURSO`; otherwise `notificado_en` is set and the user must confirm.
- If changing queue/timer logic, update both `pvd_system.py` and the UI pieces in `user_functions.py` (notifications/confirm flows and JS overlays in `notifications.py`).

## Authentication & secrets
- Credentials fall back to defaults in code for local dev but are read from `st.secrets` in production (`auth.authenticate`).
- Sessions use `st.session_state`; session expiration uses `config.SISTEMA_CONFIG_DEFAULT['sesion_horas_duracion']` and `auth.verificar_sesion()`.

## Conventions & patterns
- Avoid writing files directly — prefer `database.guardar_*` (which copies backups to `data_backup/`).
- When adding new configuration keys, add defaults to `config.py` *and* handle migrations in the related `database.cargar_*` function (see how `cargar_config_pvd()` migrates `duracion_pvd`).
- Use explicit `key=` on Streamlit widgets to avoid rerun collisions (the codebase uses widget keys extensively).
- Keep business logic in `calculation*.py`; keep UI-only code in `user_functions.py` / `ui_components.py`.

## Testing and CI
- No tests or CI workflows were found in the repository. For local verification, run the Streamlit app and exercise the flows manually (especially PVD queue transitions and data migrations). If adding tests, prefer pytest and isolate file-system effects (use temp dirs for `data/`).

## When to open a PR
- If you change data schemas, include a migration in `database.py` and add an automated backup path for the earlier format.
- If you modify PVD behavior, include a short integration checklist in the PR describing manual steps to validate (create sample `data/cola_pvd.json`, simulate queue transitions, validate notifications/confirm flow).

---
If anything here is unclear or you want more examples (e.g., typical `cola_pvd.json` lifecycle events, or which functions are safe to call from background threads), tell me which section to expand and I'll iterate. ✅

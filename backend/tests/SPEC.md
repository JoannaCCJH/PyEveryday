# SUT Behavior Spec

One paragraph per module, written from source inspection. This is the source of
truth for EP / BA / EG derivation (proposal Â§2.2). Do NOT refine by peeking at
tests; if behavior is ambiguous, clarify here first, then derive tests.

---

## scripts/utilities/password_generator.py

`PasswordGenerator` class with several generators.
- `generate_random_password(length=12, include_{upper,lower,digits,symbols}=True, exclude_ambiguous=False)`: builds a password by collecting one required char from each included type, then filling the remainder with `secrets.choice(characters)` and shuffling with `secrets.SystemRandom().shuffle`. Raises `ValueError` if `length < 4` or if all four character types are disabled. Ambiguous set = `"0O1lI"`.
- `generate_memorable_password(num_words=3, separator='-', include_numbers=True, capitalize=True)`: picks words from `word_lists` (colors/animals/objects), joins, optionally appends two digits.
- `generate_passphrase(num_words=4, min_length=6, max_length=12)`: filters word_lists by length window; if pool smaller than num_words, falls back to a hardcoded list.
- `generate_pin(length=4)`: `ValueError` if `length < 1`; returns digits-only string.
- `generate_hex_password(length=16)`: `ValueError` if `length < 4`; returns 0-9a-f string.
- `check_password_strength(password)`: scores 0â8 across length, char variety, uniqueness ratio, common-pattern avoidance; returns dict with `score`, `max_score=8`, `strength`, `feedback`, `length`, `unique_chars`.
- `generate_multiple_passwords(count=5, **kwargs)`: returns list of `{password, strength, score}` sorted by score desc.
- `generate_custom_pattern(pattern)`: L=lower, U=upper, D=digit, S=symbol, X=any alnum; any other char is a literal.

Validation points for EP/BA/EG:
- length == 3 / 4 / 5 (around lower bound); very large (1000+).
- All-False flags combination.
- `exclude_ambiguous=True` with only lowercase included.
- Pattern containing only literals; empty pattern.

---

## scripts/security/password_checker.py

`PasswordChecker` class analyzing a password.
- `calculate_entropy(password)`: charset size sums 26 (if lower), 26 (upper), 10 (digit), `len(string.punctuation)` (special). Entropy = `len * log2(charset_size)`; 0 when charset empty.
- `check_common_patterns(password)`: scans for sub-strings in `password_patterns` + a keyboard pattern list (qwerty, asdf, zxcv, 12345, 54321); case-insensitive; returns list of matches (keyboard patterns prefixed with `"keyboard pattern: "`).
- `check_character_variety(password)`: dict of booleans for lowercase/uppercase/digits/special/length_8_plus/length_12_plus.
- `check_repeated_characters(password)`: detects 3 equal consecutive chars and 4-char windows with â¤2 unique.
- `check_dictionary_words(password)`: substring match against a hardcoded word list (case-insensitive).
- `estimate_crack_time(password)`: returns 4 human-readable strings keyed by attack scenario. Uses `2**entropy / (2*rate)` formula; boundary at 60s, 3600s, 86400s, 31536000s.
- `analyze_password(password)`: returns `{'error': ...}` on empty password; otherwise full dict containing `strength_score` (capped at 12) and `strength_level` ("Very Weak" to "Very Strong").
- `get_strength_level(score)`: levels at â¤3, â¤5, â¤7, â¤9, â¤11, else "Very Strong".
- `get_recommendations(analysis)`: returns list of short suggestions.

Validation points:
- Empty string (must return `{'error': ...}`).
- One-char / single-class passwords (entropy=0 paths).
- Passwords containing exact common values ("password", "123456").
- `strength_score` cap behavior (confirm 12 is the hard ceiling).

---

## scripts/utilities/unit_converter.py

`UnitConverter` class with per-category conversion factors (base unit per category has factor 1.0).
- `convert_temperature(value, from_unit, to_unit)`: supports celsius/fahrenheit/kelvin/rankine, pivots through celsius; returns `None` only if `to_unit` is none of the four.
- `convert_standard(value, from_unit, to_unit, category)`: returns `None` if category unknown or either unit not in that category; otherwise `(value * from_factor) / to_factor`.
- `convert(value, from_unit, to_unit, category=None)`: auto-detects category via `detect_category` if not supplied; dispatches to temperature or standard. Returns `None` when no matching category.
- `detect_category(from_unit, to_unit)`: returns first category where both units are members; returns `None` when no category has both.
- `calculate_ratio(v1, u1, v2, u2, category)`: returns `None` if category missing OR `base2 == 0`. NOTE: uses `.get(unit, 0)` â unknown units silently become 0 rather than returning None, producing `0/base2 = 0.0` â **possible fault** for EG.
- `find_best_unit(value, from_unit, category)`: picks a "best" unit such that absolute converted value is â¥1 and less than current best; condition `1 <= abs(converted) < best_value or (best_value < 1 and abs(converted) >= 1)`.
- `smart_convert(value, from_unit)`: detects category, calls `find_best_unit`, prints result (side effect only).

Validation points:
- Same unit on both sides (should return input unchanged).
- Cross-category requests (e.g., kg â m) must return None.
- Negative values for length/mass (numerically meaningful but physically odd).
- Temperature absolute-zero boundary: â273.15 Â°C, 0 K, â459.67 Â°F.
- `calculate_ratio` with unknown unit (fault target).

---

## scripts/utilities/age_calculator.py

`AgeCalculator` class; uses `datetime.date.today()` by default.
- `parse_date(date_string)`: tries 8 formats (YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, YYYY/MM/DD, DD.MM.YYYY, "Month DD, YYYY", "DD Month YYYY"); raises `ValueError` if none match.
- `calculate_age(birth_date, current_date=None)`: raises `ValueError` if `birth_date > current_date`. Returns dict with years/months/weeks/days/hours/minutes/seconds (seconds derived from days*24*60*60, so leap-second-ignorant) plus `next_birthday` and `days_to_next_birthday`.
- `get_detailed_age`: returns y/m/d with borrow logic using last month's day count.
- `calculate_zodiac_sign(birth_date)`: 12 ranges; uses start-month+day OR end-month+day. Capricorn wraps Dec 22 â Jan 19. Returns `{"sign": "Unknown", "symbol": "?"}` on no match â should never happen for a valid date; **potential fault for specific boundary days** (e.g., Dec 21, Mar 20).
- `calculate_chinese_zodiac(birth_date)`: `animal_index = year % 12` against `[Monkey, Rooster, ..., Goat]`; `element_index = (year // 2) % 5` against `[Metal, Water, Wood, Fire, Earth]`. Approximation of heavenly-stems cycle â not the canonical mapping for every year.
- `calculate_life_events(birth_date)`: 8 milestone ages; status "passed"/"upcoming" relative to today.
- `compare_ages(birth1, birth2, name1, name2)`: prints only (side effect).

Validation points:
- DD/MM/YYYY vs MM/DD/YYYY ambiguous dates (e.g., "03/04/2020") â the first matching format wins (DD/MM/YYYY), which may silently misinterpret.
- Zodiac boundary days: 20th/21st/22nd/23rd of each month.
- Birth date == current date (age 0; days_to_birthday 0 or 365?).
- Feb 29 birthdays in non-leap-year "current dates".
- Future birth date (must raise).

---

## scripts/productivity/todo_manager.py

`TodoManager` persists to `todo_list.json` by default.
- `TodoItem(task, priority=Priority.MEDIUM, due_date=None)`: `created_at` auto-set from `datetime.datetime.now().isoformat()`; `completed=False`.
- `load_todos()`: returns `[]` if file missing; otherwise hydrates via `TodoItem.from_dict`. No try/except â malformed JSON crashes.
- `save_todos()`: writes list of dicts with indent=2.
- `add_task(task, priority, due_date)`: appends and saves immediately.
- `complete_task(index)` / `remove_task(index)`: bounds-checked `0 <= index < len`; prints "Invalid task index" otherwise (does NOT raise).
- `list_tasks(show_completed=False)`: prints; returns None.
- `get_today_tasks()`: filters for `due_date == today.isoformat()` AND `not completed`.
- Module-level `dashboard_summary()` (declared before the class but only evaluated at call-time) summarizes totals + next due date among pending tasks with a `due_date`.

Validation points:
- Add/complete/remove round-trip via JSON file (use `tmp_json_store`).
- Negative index to complete/remove.
- Index equal to `len(todos)`.
- Duplicate task text (should be allowed â no uniqueness constraint).
- `due_date` string not in ISO format (accepted as-is but `get_today_tasks` wonât match).

---

## scripts/productivity/reminder_system.py

`ReminderManager` persists to `reminders.json`.
- `Reminder(message, reminder_time, repeat=False, repeat_interval=None)`: `id = str(int(time.time()*1000))`; `active=True`.
- `load_reminders()` / `save_reminders()`: JSON persistence analogous to TodoManager.
- `add_reminder(message, reminder_time, repeat, repeat_interval)` returns the generated ID.
- `remove_reminder(reminder_id)`: filter out matching ID; silent if nothing matches.
- `trigger_reminder(reminder)`: prints, beeps (winsound on Windows, `\a` otherwise, try/except swallows errors). If repeat, advances `reminder_time` by interval; else sets `active=False`. Saves.
- `calculate_next_time(current_time, interval)`: interval suffix `m`/`h`/`d` (int prefix); else defaults to `+1h`.
- `check_reminders()`: triggers every active reminder where `reminder_time <= datetime.datetime.now()`.
- `parse_time_string(time_str)`: if contains `T`, uses `fromisoformat`; else `HH:MM` â today at that time, rolling forward a day if already past. Returns `None` on `ValueError`.

Validation points:
- `parse_time_string` with `HH:MM` already in the past (must roll +1 day).
- `parse_time_string` with malformed string (must return None, not raise).
- Interval with unknown suffix (falls back to +1h â intentional or fault?).
- Remove non-existent ID.
- Repeat flag with no interval.
- Two reminders created within the same millisecond (ID collision risk).

---

## scripts/data_tools/data_converter.py

`DataConverter` using pandas; supports json/csv/xml/txt/xlsx.
- `read_json` / `write_json`: JSON â DataFrame when list-of-dicts, else raw dict. Swallows all exceptions, returns None/False with a print.
- `read_csv` / `write_csv`: thin `pd.read_csv` / `to_csv` wrappers.
- `read_excel` / `write_excel`: via openpyxl.
- `read_xml`: expects root-with-items; returns list of dicts with attribute keys prefixed `@`.
- `write_xml`: prettyprints with minidom.
- `flatten_json(data, separator='.')`: recursive flatten; lists become JSON-encoded string values (a lossy choice worth asserting).
- `unflatten_json(data, separator='.')`: inverse via dotted keys.
- `validate_json(file_path)`: `(ok, msg)`.
- `validate_csv(file_path, expected_columns=None)`: `(ok, msg)`; empty/unreadable fails; missing/extra columns fails.
- `compare_data(file1, file2)`: `{equal, reason, record1?, record2?}` or None if either read fails; ordered record-by-record comparison (NOT order-insensitive).
- `auto_read(file_path)`: dispatches on extension (case-insensitive); unknown extension â None + print.
- `convert_file(input, output)`: tabular targets (csv, xlsx) require list-of-dicts or DataFrame; otherwise raises `ValueError` â caught, returns False.
- `sanitize_data(df)`: strips string columns, fills NaN with `''`. Mutates input.
- `preview(file_path, n=5)`: print-only side effect.

Validation points:
- `flatten_json` round-trip loses list structure (confirm via unflatten).
- `compare_data` two identical CSVs with rows in different order (expect NOT equal; documents the contract).
- `convert_file`: json â csv when JSON is a scalar or top-level dict (must return False, not crash).
- Unicode column names / emoji data in sanitize.
- File with BOM or odd delimiters in CSV.

---

## scripts/automation/auto_email_sender.py

`EmailSender` class; primary **SMTP mock** target.
- `__init__(config_file="email_config.json")`: loads JSON config if it exists, otherwise uses a default dict (gmail smtp, port 587, empty credentials).
- `load_config(config_file)`: no try/except â malformed JSON crashes.
- `send_email(recipient, subject, body, attachments=None)`: builds a MIMEMultipart message, optionally attaches files (silently **skipped** if path does not exist â line 36), opens `smtplib.SMTP`, `starttls`, `login`, `sendmail`, `quit`. Returns True on success, False on any exception (caught broadly). Prints on both paths.
- `send_bulk_emails(recipient_list, subject, body, attachments=None)`: iterates `send_email` per recipient, tallies success count, prints summary. Returns None (no explicit return).

Validation points (mock `smtplib.SMTP`):
- Happy path: assert `SMTP(server, port)`, `starttls`, `login(email, password)`, `sendmail(from, to, body)`, `quit` are called in order.
- `login` raises `SMTPAuthenticationError` â returns False (swallowed).
- `sendmail` raises `SMTPRecipientsRefused` â returns False.
- Empty recipient string â MIME accepts it, SMTP call still made (documents behavior).
- Attachment path that does not exist â silently skipped (no error), email still sent without the attachment â **possible fault for EG** (user expects either attachment or error).
- `send_bulk_emails` with an empty list â prints "0/0", never calls smtplib.
- Config file with missing `sender_email` key â `KeyError` from `send_email`, caught â returns False.

---

## scripts/web_scraping/weather_checker.py

`WeatherChecker` class; primary **mock-testing** target.
- `__init__(api_key=None)`: no-op other than storing key and base URLs.
- `get_weather_by_city(city, units="metric")`: if no API key, delegates to `get_weather_free`. Otherwise hits `{base_url}/weather` with `q,appid,units`, 10s timeout. On `RequestException` â falls back to free; on other `Exception` â returns None.
- `get_weather_by_coordinates(lat, lon, units)`: requires API key; returns None if absent.
- `get_weather_forecast(city, days=5, units)`: requires API key; requests `cnt=days*8`.
- `get_weather_free(city)`: hits `https://wttr.in/{city}?format=j1`.
- `format_weather_data(data, units)`: accesses `data["name"]`, `data["sys"]["country"]`, `data["main"]["temp"]`, â¦, `data["weather"][0]["description"]`, `data["wind"]["speed"]`. Uses `data.get("visibility", "N/A")` only for visibility. â **Any missing non-visibility key raises KeyError, which is not caught at this layer.**
- `format_forecast_data`: iterates `data["list"][:40:8]`; also KeyError-prone on missing fields.
- `format_wttr_data(data)`: expects wttr's `current_condition[0]` shape.
- `save_weather_data(weather, filename)`: appends to log JSON, tolerating missing/corrupt file.

Validation points (mock `requests.get`):
- Canned successful OpenWeather JSON â parsed dict matches spec.
- 404 / 500 status â `raise_for_status` triggers `RequestException` â free fallback is called.
- `requests.Timeout` â same fallback path.
- Malformed JSON body (valid HTTP 200 but `response.json()` raises) â caught by the broader `except Exception` â returns None.
- Missing `data['wind']` in a 200 response â KeyError bubbles. Document whether this is intended.
- `get_weather_by_coordinates` with no api_key â returns None (no request made).

---

## scripts/automation/file_organizer.py

Two functions.
- `organize_files_by_extension(source_dir)`: iterates top-level entries; for each file, computes `Path(filename).suffix.lower()[1:]` (or `"no_extension"`), creates a subfolder, `shutil.move`s the file in. Catches per-file exceptions with a print. Non-existent source prints and returns.
- `organize_files_by_date(source_dir)`: groups by `YYYY-MM` of `stat.st_ctime`.

Validation points (use `tmp_path`):
- Mixed extensions, ensure each goes to its own folder.
- File without extension â `no_extension/`.
- Hidden dotfile `.bashrc` â `Path("/x/.bashrc").suffix == ""`, so goes to `no_extension/` (documents the behavior).
- File extension `.TAR.GZ` (multi-dot) â suffix is `.gz` only; file named like `a.tar.gz` goes into `gz/`, not `tar.gz/`.
- Subdirectory in source â skipped (not a file).
- Collision: existing `<ext>/<filename>` already present â `shutil.move` raises, caught, prints error.

---

## routers/auth/router.py

Only router mounted in `backend/app.py`.
- `POST /api/v1.0/auth/Signup` (note the capital S) â `async def create_user(user_data: UserCreate): pass`. Returns 201 with empty body on any valid payload. No persistence, no validation beyond what Pydantic enforces.

Validation points:
- Valid payload â 201, empty body.
- Invalid payload (missing required field, wrong types) â 422 from Pydantic.
- Wrong HTTP method (GET /Signup) â 405.
- Wrong path casing (`/signup`) â 404.

---

# Gaps & Blockers discovered during Step 1

1. **`ip_address.py` dropped from scope.** Top-level `input()` call blocks on import and `dec_bin` is undefined â untestable as-is. Replaced with `automation/auto_email_sender.py` (SMTP mock target).
2. **Auth router is a stub (`pass`).** Signup does nothing. API tests will verify Pydantic schema validation only; the "propagation of validation errors" goal in proposal Â§2.3 is limited by there being no business logic. Flag this in the final report.
3. **`password_generator` uses `secrets.choice`, not `random.choice`.** Our `fixed_random` fixture in `conftest.py` only seeds `random` â it will NOT make this module deterministic. Needs a separate fixture that patches `secrets.choice` / `secrets.randbelow` / `secrets.SystemRandom.shuffle`.
4. **`todo_manager.py` / `reminder_system.py` default filenames are `todo_list.json` / `reminders.json`, which already exist at repo root.** `tmp_json_store` fixture (cwd change to tmp_path) correctly isolates writes, but tests must instantiate the manager AFTER the fixture applies, or pass an explicit filename.
5. **`file_organizer.py` has no `if __name__ == "__main__":` guard around imports** (argparse-like dispatch is inside `__main__` block â OK). Safe to import.
6. **Potential real faults to target deliberately (fault-hunting per rubric):**
   - `password_generator.generate_random_password(exclude_ambiguous=True)` may still emit ambiguous chars via the `required_chars` path (sources lower/upper/digits from the *unfiltered* sets on lines 34, 40, 47).
   - `unit_converter.calculate_ratio` silently returns `0.0` for unknown units instead of `None`.
   - `age_calculator.calculate_zodiac_sign` has a "Unknown" fallback that may fire for specific boundary dates.
   - `weather_checker.format_weather_data` crashes on any missing required key (except `visibility`) â inconsistent error handling.

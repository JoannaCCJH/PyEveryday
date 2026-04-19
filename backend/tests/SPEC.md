# SUT Behavior Spec

One short paragraph per module, written BEFORE black-box tests are designed.
This is the source of truth for EP / BA / EG test derivation (proposal Â§2.2).

## scripts/utilities/password_generator.py
_TODO: expected inputs, valid ranges, guarantees about output composition._

## scripts/security/password_checker.py
_TODO: strength levels, rules that bump/penalize score, return shape._

## scripts/utilities/unit_converter.py
_TODO: supported unit families, error behavior for unsupported units._

## scripts/utilities/age_calculator.py
_TODO: accepted date formats, handling of future dates / invalid dates._

## scripts/utilities/currency_converter.py
_TODO: supported currencies, behavior when the network call fails (mocked)._

## scripts/productivity/todo_manager.py
_TODO: create/update/delete contract, persistence file, duplicate handling._

## scripts/productivity/reminder_system.py
_TODO: reminder fields, due-time semantics, persistence file._

## scripts/data_tools/data_converter.py
_TODO: supported source/target formats, schema of accepted inputs, error paths for unsupported or malformed data._

## scripts/security/ip_address.py
_TODO: accepted IP/mask formats, NetID/HostID derivation rules, behavior on invalid octets or masks (boundary-heavy)._

## scripts/web_scraping/weather_checker.py
_TODO: expected request URL/params, parsing contract over the JSON/HTML response, behavior when network call fails, times out, or returns malformed data. Network is mocked._

## scripts/automation/file_organizer.py
_TODO: classification rules (extension -> category folder), handling of unknown extensions, duplicates, hidden files. Filesystem ops tested against tmp_path._

## routers/auth/router.py
_TODO: endpoints, required fields, success/error status codes._

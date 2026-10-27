# Retired tests (Oct 26 2026, v6.2.1)

These 36 tests were written for earlier versions and no longer describe how BuildersPro
should behave. Stan retired them so that a failing test always means a real problem.

Why each one is out of date:
- 34 check a specific old version number (e.g. "version is 4.43") and/or a screen that
  was later redesigned on purpose (punch status cells you tap, the shopping list without
  cells, the Subs | Clients phone-book switch, the Job Sections menu, the silent sync pill).
  Every other check in them passed on v6.2.0 before they were retired.
- test_v343 flagged the invisible tap area over Punch "Status" cells as an overlap —
  that cell-is-the-button design was asked for (Oct 2026).
- test_v383 was a one-off investigation script, not a pass/fail test.

They are kept here (not deleted) for reference. They do not run.

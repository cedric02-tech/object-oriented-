# Hostel Borrowing Club

A small, runnable model of the club from the UML:

- **Abstraction:** `Item` and `User` are abstract; you cannot create them directly.
- **Inheritance:** `Book`, `Pen`, `Pencil`, `Calculator`, `PhoneCharger`, and
  `ElectricIron` extend `Item`. `Member` and `Admin` extend `User`.
- **Polymorphism:** every item answers `loan_days`, `daily_fine`,
  `replacement_cost`, and `care_note` in its own way, and the club treats them
  all the same.
- **Duck typing:** notifiers (`ConsoleNotifier`, `SMSNotifier`) and enforcer
  rules share no base class. Anything with `.send(...)` is a notifier; anything
  with `.check(...)` is a rule.
- **Objects:** the demo at the bottom creates real objects and runs a scenario.

Run it with:

```text
python hostel_borrowing_club.py
```

Money is in Uganda shillings (UGX).

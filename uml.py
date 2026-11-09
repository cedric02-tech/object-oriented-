#HOSTEL BORROWING CLUB (UML)
"""Enum definitions for the hostel borrowing club."""

from abc import ABC, abstractmethod
from enum import Enum
from itertools import count



# Enumerations By Cedric Charles B33243
class Condition(Enum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    DAMAGED = "damaged"


class ItemStatus(Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"
    UNDER_REPAIR = "under repair"
    LOST = "lost"


class LoanStatus(Enum):
    ACTIVE = "active"
    OVERDUE = "overdue"
    RETURNED = "returned"
    LOST = "lost"

    # ABSTRACTION + INHERITANCE + POLYMORPHISM: items
class Item(ABC):

    _ids = count(1)

    def __init__(self, name, condition=Condition.GOOD):
        self.item_id = next(self._ids)
        self.name = name
        self.condition = condition
        self.status = ItemStatus.AVAILABLE

    # Each subclass is a corelation (abstraction).
    @property
    @abstractmethod
    def loan_days(self):
        """Maximum number of days this item may be kept."""

    @property
    @abstractmethod
    def daily_fine(self):
        """UGX charged for each day the item is late."""

    @property
    @abstractmethod
    def replacement_cost(self):
        """UGX charged if the item is lost (also caps late fines)."""

    # Optional overrides with a sensible default.
    @property
    def deposit(self):
        """Refundable deposit taken at borrowing time. Most items need none."""
        return 0

    def care_note(self):
        return "Handle with care and return it as you found it."

    def is_lendable(self):
        return self.status is ItemStatus.AVAILABLE and self.condition is not Condition.DAMAGED

    def __str__(self):
        return f"#{self.item_id} {self.name} [{self.status.value}, {self.condition.value}]"


class Book(Item):
    loan_days = 14
    daily_fine = 500
    replacement_cost = 30_000

    def care_note(self):
        return "No writing, no folded pages, keep it dry."


class Pen(Item):
    loan_days = 3
    daily_fine = 200
    replacement_cost = 1_500

    def care_note(self):
        return "Cap it after use."


class Pencil(Item):
    loan_days = 3
    daily_fine = 100
    replacement_cost = 500

    def care_note(self):
        return "Sharpened pencils are returned sharpened."


class Calculator(Item):
    loan_days = 7
    daily_fine = 1_000
    replacement_cost = 45_000
    deposit = 5_000

    def care_note(self):
        return "Return it with batteries in and the cover on."


class PhoneCharger(Item):
    loan_days = 2
    daily_fine = 1_000
    replacement_cost = 20_000
    deposit = 5_000

    def care_note(self):
        return "Return the plug AND the cable."


class ElectricIron(Item):
    loan_days = 1
    daily_fine = 2_000
    replacement_cost = 60_000
    deposit = 10_000

    def care_note(self):
        return "Unplug it, let it cool, empty the water."

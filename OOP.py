
from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum


class LoanStatus(Enum):
    ACTIVE = "active"
    OVERDUE = "overdue"


class User(ABC):
    def __init__(self, name, phone):
        self.name = name
        self.phone = phone
 
    @property
    @abstractmethod
    def role(self):
        """Who this person is in the club."""
 
    def __str__(self):
        return f"{self.name} ({self.role})"
 
 
class Member(User):
    role = "member"
 
    def __init__(self, name, phone, room, channel):
        super().__init__(name, phone)
        self.room = room
        self.channel = channel          # DUCK TYPED: anything with .send(member, text)
        self.loans = []                 # active loans
        self.strikes = 0
        self.trust_score = 100
        self.unpaid_fines = 0
        self.suspended = False
 
 
class Admin(User):
    role = "admin"
 
 
# ----------------------------------------------------------------------------
# DUCK TYPING: notifiers. No shared parent class, just a .send() method.
# ----------------------------------------------------------------------------
class ConsoleNotifier:
    def send(self, member, text):
        print(f"      [screen to {member.name}] {text}")
 
 
class SMSNotifier:
    def send(self, member, text):
        print(f"      [SMS to {member.phone}] {text}")
 
 
# ----------------------------------------------------------------------------
# DUCK TYPING: enforcer rules. Each has .check(member, item) -> reason or None.
# ----------------------------------------------------------------------------
class ItemMustBeLendable:
    def check(self, member, item):
        if not item.is_lendable():
            return f"{item.name} is not available ({item.status.value}, {item.condition.value})."
 
 
class NotSuspended:
    def check(self, member, item):
        if member.suspended:
            return "Your membership is suspended after repeated mismanagement."
 
 
class NoUnpaidFines:
    def check(self, member, item):
        if member.unpaid_fines > 0:
            return f"Clear your fines first (UGX {member.unpaid_fines:,})."
 
 
class NoOverdueLoans:
    def check(self, member, item):
        if any(l.status is LoanStatus.OVERDUE for l in member.loans):
            return "Return your overdue items before borrowing more."
 
 
class MinimumTrust:
    def __init__(self, minimum=40):
        self.minimum = minimum
 
    def check(self, member, item):
        if member.trust_score < self.minimum:
            return f"Trust score {member.trust_score} is below the minimum of {self.minimum}."
 
 
class MaxActiveLoans:
    def __init__(self, limit=3):
        self.limit = limit
 
    def check(self, member, item):
        if len(member.loans) >= self.limit:
            return f"Limit reached: you already hold {self.limit} items."
 
 
# ----------------------------------------------------------------------------
# Loan: one borrowing event (the BorrowRequest of the class diagram)
# ----------------------------------------------------------------------------
class Loan:
    def __init__(self, member, item, borrowed_on, days):
        self.member = member
        self.item = item
        self.borrowed_on = borrowed_on
        self.due_on = borrowed_on + timedelta(days=days)
        self.deposit_paid = item.deposit
        self.returned_on = None
        self.status = LoanStatus.ACTIVE
        self.reminded = False
 
    def days_late(self, today):
        end = self.returned_on or today
        return max(0, (end - self.due_on).days)
 
    def is_overdue(self, today):
        return self.returned_on is None and today > self.due_on
 
 
# ----------------------------------------------------------------------------
# THE ENFORCER: the part that deals with mismanagement
# ----------------------------------------------------------------------------
class Enforcer:
    STRIKE_LIMIT = 3
    TRUST_PENALTY = 15
    DAMAGE_RATE = 0.5          # damaged item costs 50% of replacement cost
 
    def __init__(self, rules):
        self.rules = rules     # any objects that have .check(member, item)
 
    def blockers(self, member, item):
        return [r for rule in self.rules if (r := rule.check(member, item))]
 
    def late_fine(self, loan, today):
        fine = loan.days_late(today) * loan.item.daily_fine
        return min(fine, loan.item.replacement_cost)    # never more than item is worth
 
    def damage_fee(self, item):
        return int(item.replacement_cost * self.DAMAGE_RATE)
 
    def strike(self, member, reason, channel_notify):
        member.strikes += 1
        member.trust_score = max(0, member.trust_score - self.TRUST_PENALTY)
        channel_notify(member, f"Strike {member.strikes}/{self.STRIKE_LIMIT}: {reason}")
        if member.strikes >= self.STRIKE_LIMIT and not member.suspended:
            member.suspended = True
            channel_notify(member, "You are now SUSPENDED. Speak to the admin.")
 
 
# ----------------------------------------------------------------------------
# The club itself
# ----------------------------------------------------------------------------
class BorrowingClub:
    def __init__(self, name, admin, enforcer):
        self.name = name
        self.admin = admin
        self.enforcer = enforcer
        self.items = []
        self.members = []
        self.loans = []
 
    # --- setup -------------------------------------------------------------
    def add_item(self, item):
        self.items.append(item)
        return item
 
    def register(self, member):
        self.members.append(member)
        return member
 
    def _tell(self, member, text):
        member.channel.send(member, text)       # duck typing in action
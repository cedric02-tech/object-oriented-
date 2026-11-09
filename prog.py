from datetime import date, timedelta

from OOP import (
    Admin,
    BorrowingClub as BaseBorrowingClub,
    ConsoleNotifier,
    Enforcer,
    ItemMustBeLendable,
    Loan,
    LoanStatus,
    MaxActiveLoans,
    Member,
    MinimumTrust,
    NoOverdueLoans,
    NoUnpaidFines,
    NotSuspended,
    SMSNotifier,
)
from uml import (
    Book,
    Calculator,
    Condition,
    ElectricIron,
    ItemStatus,
    Pen,
    Pencil,
    PhoneCharger,
)


class BorrowingClub(BaseBorrowingClub):
    # --- availability: "can I take this, and if not, why?" -----------------
    def availability(self, item, today):
        """Return (ok, message). The message always explains the status."""
        if item.status is ItemStatus.LOST:
            return False, "Not available: this item was lost and is no longer in stock."
        if item.status is ItemStatus.UNDER_REPAIR or item.condition is Condition.DAMAGED:
            return False, "Not available: it is damaged and waiting for repair."
        if item.status is ItemStatus.BORROWED:
            loan = next((l for l in self.loans
                         if l.item is item and l.returned_on is None
                         and l.status in (LoanStatus.ACTIVE, LoanStatus.OVERDUE)), None)
            if loan is None:
                return False, "Not available: it is currently out."
            if loan.is_overdue(today):
                return False, (f"Not available: held by {loan.member.name}, "
                               f"overdue by {loan.days_late(today)} day(s) (was due {loan.due_on:%a %d %b}).")
            left = (loan.due_on - today).days
            return False, (f"Not available: borrowed by {loan.member.name}, "
                           f"back {loan.due_on:%a %d %b} (in {left} day(s)).")
        return True, f"Available now. You may keep it up to {item.loan_days} day(s)."
 
    def catalogue(self, today):
        print(f"\n[Catalogue, {today:%a %d %b %Y}]")
        for item in self.items:
            ok, msg = self.availability(item, today)
            print(f"  {'YES' if ok else 'NO '} {item.name:<26} {msg}")
 
    def pick(self, member, item, today, days=None):
        """Member chooses an item: show availability first, borrow only if free."""
        print(f"\n  {member.name} picks {item.name}")
        ok, msg = self.availability(item, today)
        print(f"    -> {msg}")
        if not ok:
            return None
        return self.borrow(member, item, today, days)     # member rules still apply
 
    # --- borrowing ---------------------------------------------------------
    def borrow(self, member, item, today, days=None):
        problems = self.enforcer.blockers(member, item)
        if problems:
            print(f"  X {member.name} cannot borrow {item.name}:")
            for p in problems:
                print(f"      - {p}")
            return None
 
        days = min(days or item.loan_days, item.loan_days)   # cannot exceed the item limit
        loan = Loan(member, item, today, days)
        item.status = ItemStatus.BORROWED
        member.loans.append(loan)
        self.loans.append(loan)
        print(f"  + {member.name} borrowed {item.name}, due {loan.due_on:%a %d %b}"
              f"{f', deposit UGX {loan.deposit_paid:,}' if loan.deposit_paid else ''}.")
        self._tell(member, f"Care note: {item.care_note()}")
        return loan
 
    def _close(self, loan, today, charges):
        """Settle money: deposit first, any remainder becomes an unpaid fine."""
        member = loan.member
        member.loans.remove(loan)
        refund = max(0, loan.deposit_paid - charges)
        owed = max(0, charges - loan.deposit_paid)
        member.unpaid_fines += owed
        if charges == 0:
            self._tell(member, f"Thanks! Deposit refunded: UGX {refund:,}." if refund else "Thanks for returning it on time.")
        else:
            self._tell(member, f"Charges UGX {charges:,}. Deposit refunded UGX {refund:,}. Still owed UGX {owed:,}.")
 
    def return_item(self, loan, today, condition=Condition.GOOD):
        loan.returned_on = today
        loan.status = LoanStatus.RETURNED
        item, member = loan.item, loan.member
 
        late = self.enforcer.late_fine(loan, today)
        damage = self.enforcer.damage_fee(item) if condition is Condition.DAMAGED else 0
 
        item.condition = condition
        item.status = ItemStatus.UNDER_REPAIR if damage else ItemStatus.AVAILABLE
        print(f"  < {member.name} returned {item.name} on {today:%a %d %b}"
              f" ({loan.days_late(today)} days late, condition {condition.value}).")
 
        if late:
            self.enforcer.strike(member, f"{item.name} returned {loan.days_late(today)} day(s) late.", self._tell)
        if damage:
            self.enforcer.strike(member, f"{item.name} returned damaged.", self._tell)
        self._close(loan, today, late + damage)
 
    def report_lost(self, loan, today):
        loan.status = LoanStatus.LOST
        loan.item.status = ItemStatus.LOST
        print(f"  ! {loan.member.name} lost {loan.item.name}.")
        self.enforcer.strike(loan.member, f"{loan.item.name} was lost.", self._tell)
        self._close(loan, today, loan.item.replacement_cost)
 
    def pay_fines(self, member, amount):
        paid = min(amount, member.unpaid_fines)
        member.unpaid_fines -= paid
        print(f"  $ {member.name} paid UGX {paid:,}. Remaining fines: UGX {member.unpaid_fines:,}.")
 
    # --- daily enforcement -------------------------------------------------
    def daily_check(self, today):
        print(f"\n[Daily check, {today:%a %d %b %Y}]")
        for loan in list(self.loans):
            if loan.returned_on or loan.status is LoanStatus.LOST:
                continue
            member = loan.member
            if loan.is_overdue(today):
                loan.status = LoanStatus.OVERDUE
                fine = self.enforcer.late_fine(loan, today)
                self._tell(member, f"OVERDUE: {loan.item.name}, {loan.days_late(today)} day(s) late, "
                                   f"fine so far UGX {fine:,}.")
            elif (loan.due_on - today).days <= 1 and not loan.reminded:
                loan.reminded = True
                self._tell(member, f"Reminder: {loan.item.name} is due {loan.due_on:%a %d %b}.")
 
    # --- dashboard ---------------------------------------------------------
    def dashboard(self, today):
        active = [l for l in self.loans if l.returned_on is None and l.status is not LoanStatus.LOST]
        return {
            "total items": len(self.items),
            "available": sum(i.status is ItemStatus.AVAILABLE for i in self.items),
            "items out": len(active),
            "overdue": sum(l.is_overdue(today) for l in active),
            "lost / repair": sum(i.status in (ItemStatus.LOST, ItemStatus.UNDER_REPAIR) for i in self.items),
            "members": len(self.members),
            "suspended": sum(m.suspended for m in self.members),
            "fines owed (UGX)": sum(m.unpaid_fines for m in self.members),
        }
 
 
# ----------------------------------------------------------------------------
# DEMO: objects in action
# ----------------------------------------------------------------------------
def main():
    enforcer = Enforcer(rules=[
        ItemMustBeLendable(), NotSuspended(), NoUnpaidFines(),
        NoOverdueLoans(), MinimumTrust(40), MaxActiveLoans(3),
    ])
    club = BorrowingClub("Hostel Borrowing Club", Admin("Warden Ssali", "0700000000"), enforcer)
 
    # Six items, six different classes, one shared interface.
    book, pen, pencil, calc, charger, iron = (
        club.add_item(Book("Database Systems textbook")), club.add_item(Pen("Blue pen")),
        club.add_item(Pencil("HB pencil")), club.add_item(Calculator("Casio fx-991")),
        club.add_item(PhoneCharger("Type-C charger")), club.add_item(ElectricIron("Steam iron")),
    )
 
    # Members use different notifiers; the club never checks their type.
    aisha = club.register(Member("Aisha", "0771111111", "B12", SMSNotifier()))
    brian = club.register(Member("Brian", "0772222222", "C03", ConsoleNotifier()))
    okello = club.register(Member("Okello", "0773333333", "A07", ConsoleNotifier()))
 
    print("POLYMORPHISM: same questions, different answers")
    for it in club.items:
        print(f"  {type(it).__name__:<13} {it.loan_days:>2} days | late UGX {it.daily_fine:>5,}/day | "
              f"deposit UGX {it.deposit:>6,} | {it.care_note()}")
 
    day = date(2026, 11, 3)
    print(f"\n--- Day 0: {day:%a %d %b} ---")
    club.catalogue(day)                           # everything is free
    l1 = club.pick(aisha, book, day)
    l2 = club.pick(aisha, pen, day)
    l3 = club.pick(aisha, pencil, day)
    club.pick(aisha, calc, day)                   # free, but member limit of 3 blocks her
    l_iron = club.pick(brian, iron, day)
    l_charger = club.pick(okello, charger, day)
    club.pick(brian, pen, day)                    # item is out: shows who has it and when it is back
    club.catalogue(day)
 
    club.daily_check(day + timedelta(days=1))     # reminders go out
    club.daily_check(day + timedelta(days=4))     # overdue notices
 
    print(f"\n--- Day 4 ---")
    club.return_item(l_iron, day + timedelta(days=4))           # 3 days late
    club.return_item(l2, day + timedelta(days=4))               # pen, 1 day late
    club.report_lost(l_charger, day + timedelta(days=4))        # lost charger
    club.catalogue(day + timedelta(days=4))
    club.pick(brian, charger, day + timedelta(days=4))          # lost: explains why
 
    print(f"\n--- Day 5: Okello tries again ---")
    club.pick(okello, calc, day + timedelta(days=5))            # free, but blocked by his fines
    club.pay_fines(okello, 15_000)
    cal = club.pick(okello, calc, day + timedelta(days=5))
    club.return_item(cal, day + timedelta(days=6), Condition.DAMAGED)   # strike 2 + damage
 
    print(f"\n--- Day 7: Okello's third strike ---")
    club.pay_fines(okello, 99_999)
    club.pick(aisha, calc, day + timedelta(days=7))             # damaged: explains why
    pen_loan = club.pick(okello, pen, day + timedelta(days=7))
    club.return_item(pen_loan, day + timedelta(days=12))        # 2 days late
    club.pick(okello, pencil, day + timedelta(days=13))         # item overdue with Aisha
 
    print("\n=== DASHBOARD ===")
    for k, v in club.dashboard(day + timedelta(days=13)).items():
        print(f"  {k:<18} {v}")
    print("\nMember standing:")
    for m in club.members:
        print(f"  {m.name:<7} strikes {m.strikes}, trust {m.trust_score:>3}, fines UGX {m.unpaid_fines:,}, "
              f"{'SUSPENDED' if m.suspended else 'active'}")
 
 
if __name__ == "__main__":
    main()
"""Accounts: a new account's password (the one Lisul chose, else a random one, KAN-838), and resetting the
password of an Employer account Lisul made himself, which Keychain has none for. With a fake Keychain and a fake
mailbox."""

from datetime import datetime, timedelta

import pytest
from fakes import FakeClock, FakeMailbox

from apply.accounts import MAIL_WAIT, RULE, Accounts, broken_rule
from apply.keychain import CHOSEN, InMemoryKeychain
from apply.model import Handoff

SITE = "caci.wd1.myworkdayjobs.com"
EMAIL = "test.person@example.com"
NOW = datetime(2026, 10, 15, 9, 30)


def test_a_reset_password_is_in_keychain_before_the_site_is_asked_for_the_reset():
    keychain = InMemoryKeychain()
    accounts = Accounts(keychain, FakeMailbox(), FakeClock(NOW), EMAIL, "CACI")

    password = accounts.reset_password(SITE)

    assert keychain.password(SITE) == password
    assert len(password) >= 12


def test_without_gmail_a_code_is_never_waited_for_and_the_handoff_needs_sign_in_saying_why():
    mailbox = FakeMailbox(set_up=False)
    accounts = Accounts(InMemoryKeychain(), mailbox, FakeClock(NOW), EMAIL, "CACI")

    with pytest.raises(Handoff) as handoff:
        accounts.code("from:(icims.com)", NOW)
    assert str(handoff.value) == ("Needs sign-in: Gmail isn't set up for Apply: no Gmail app password in Keychain, "
                                  "so the verification code can't be read.")
    assert mailbox.looks == 0


def test_without_gmail_no_password_is_reset_and_the_handoff_says_why():
    keychain = InMemoryKeychain()
    accounts = Accounts(keychain, FakeMailbox(set_up=False), FakeClock(NOW), EMAIL, "CACI")

    with pytest.raises(Handoff) as handoff:
        accounts.reset_password(SITE)
    assert str(handoff.value).startswith(
        f"{SITE} already has an account for {EMAIL}, and Keychain has no password for it. "
        "Apply resets its password through Gmail, but Gmail isn't set up"
    )
    assert keychain.password(SITE) is None


def test_a_code_that_never_comes_is_waited_for_about_10_minutes_once_then_needs_lisul():
    # American Express on Oracle (live): Apply asked for a new code after a wait. It never asks again now.
    mailbox = FakeMailbox()
    clock = FakeClock(NOW)
    accounts = Accounts(InMemoryKeychain(), mailbox, clock, EMAIL, "CACI")

    with pytest.raises(Handoff) as handoff:
        accounts.code("from:(icims.com)", NOW)

    assert str(handoff.value).startswith("Needs sign-in: Type the emailed code: no verification code from icims.com")
    assert clock.now() - NOW >= MAIL_WAIT >= timedelta(minutes=10)
    assert "came within about 10 minutes" in str(handoff.value)


def test_a_code_that_comes_after_minutes_is_still_read():
    # JPMorgan on Oracle (live): the mail took about 2.5 minutes, past the old 2-minute wait.
    mailbox = FakeMailbox()

    def mail_comes_late():
        if clock.now() - NOW >= timedelta(minutes=9, seconds=30):
            mailbox.deliver("from:(icims.com)", code="482913")

    clock = FakeClock(NOW, on_sleep=mail_comes_late)
    accounts = Accounts(InMemoryKeychain(), mailbox, clock, EMAIL, "CACI")

    assert accounts.code("from:(icims.com)", NOW) == "482913"


CHOSEN_PASSWORD = "Fake!Chosen7xQ"  # made up, and it keeps the rule


def test_a_new_account_gets_the_password_lisul_chose_saved_for_its_site():
    keychain = InMemoryKeychain({CHOSEN: CHOSEN_PASSWORD})
    accounts = Accounts(keychain, FakeMailbox(), FakeClock(NOW), EMAIL, "CACI")

    assert accounts.new_password(SITE) == CHOSEN_PASSWORD
    assert keychain.password(SITE) == CHOSEN_PASSWORD  # the site keeps its own copy


def test_a_password_chosen_later_is_only_for_later_accounts():
    keychain = InMemoryKeychain({CHOSEN: CHOSEN_PASSWORD})
    accounts = Accounts(keychain, FakeMailbox(), FakeClock(NOW), EMAIL, "CACI")
    accounts.new_password(SITE)

    keychain.save(CHOSEN, "Fake@Changed9yR")

    assert keychain.password(SITE) == CHOSEN_PASSWORD
    assert accounts.new_password("xcel.wd1.myworkdayjobs.com") == "Fake@Changed9yR"


def test_with_no_chosen_password_each_account_gets_a_random_one_that_keeps_the_rule():
    keychain = InMemoryKeychain()
    accounts = Accounts(keychain, FakeMailbox(), FakeClock(NOW), EMAIL, "CACI")

    made = {accounts.new_password(f"t{n}.wd1.myworkdayjobs.com") for n in range(50)}

    assert len(made) == 50 and all(broken_rule(password) is None for password in made)
    assert keychain.password(CHOSEN) is None  # Apply never chooses for Lisul


@pytest.mark.parametrize("password", [
    "Short-1!a",               # under 12
    "Far-Too-Long-Password-1!",  # over 16
    "no-upper-case-1!",
    "NO-LOWER-CASE-1!",
    "No-Digits-Here!!",
    "NoSymbolAtAll123",
    "Has a space 1!Aa",
    "Bad-Symbol-1&Aaa",        # & is not one of ! @ # $ % *
    "Ünïcode-Letter1!",
])
def test_a_password_that_breaks_the_rule_says_the_rule(password):
    assert broken_rule(password) == f"Use {RULE}."


def test_a_password_that_keeps_the_rule_is_taken():
    assert broken_rule(CHOSEN_PASSWORD) is None
    assert broken_rule("Aa1!Aa1!Aa1!") is None  # 12, the shortest
    assert broken_rule("Aa1@Bb2#Cc3$Dd4%") is None  # 16, the longest


def test_a_refused_account_forgets_its_password_and_needs_lisul():
    keychain = InMemoryKeychain({CHOSEN: CHOSEN_PASSWORD})
    accounts = Accounts(keychain, FakeMailbox(), FakeClock(NOW), EMAIL, "CACI")
    accounts.new_password(SITE)

    handoff = accounts.refused(SITE, "Workday said: 'Password must not contain your email.'")

    assert keychain.password(SITE) is None and keychain.password(CHOSEN) == CHOSEN_PASSWORD
    assert str(handoff) == (f"{SITE} refused the new account (Workday said: 'Password must not contain your email.'). "
                            "If it refused the password, make the account on the page yourself with a password it "
                            "takes, then finish the form.")

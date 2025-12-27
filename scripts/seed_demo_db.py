"""Seed the demo SQLite database with realistic sample data."""

from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Tuple

# Data distributions and constants
COUNTRIES = ["US", "IN", "UK", "DE", "SG"]
PLANS = [("free", 0.6), ("pro", 0.3), ("enterprise", 0.1)]
PAYMENT_STATUSES = [("success", 0.8), ("failed", 0.2)]
EVENT_TYPES = ["signup", "login", "checkout", "logout"]
TICKET_CATEGORIES = [("billing", 0.45), ("login", 0.35), ("performance", 0.2)]
TICKET_STATUSES = [("open", 0.55), ("closed", 0.45)]

FIRST_NAMES = [
    "Alex",
    "Sam",
    "Jordan",
    "Taylor",
    "Priya",
    "Rohan",
    "Mei",
    "Lena",
    "Marco",
    "Sara",
    "Daniel",
    "Aisha",
    "Jonas",
    "Kavya",
    "Omar",
    "Sofia",
    "Anya",
    "Leo",
    "Grace",
    "Felix",
]

LAST_NAMES = [
    "Patel",
    "Smith",
    "Khan",
    "Chen",
    "Garcia",
    "Schmidt",
    "Iyer",
    "Singh",
    "Brown",
    "Davis",
    "Martin",
    "Wilson",
    "Taylor",
    "Anderson",
    "Thompson",
    "Thomas",
    "Jackson",
    "White",
    "Harris",
    "Clark",
]

DOMAINS = ["example.com", "product.io", "saasapp.com", "datacloud.net"]

USERS_TARGET = 800
PAYMENTS_MIN, PAYMENTS_MAX = 1500, 2500
EVENTS_MIN, EVENTS_MAX = 3000, 5000
TICKETS_MIN, TICKETS_MAX = 200, 400
DAYS_BACK = 90


def get_db_path() -> Path:
    """Return path to the demo database adjacent to the project root."""
    return Path(__file__).resolve().parent.parent / "data" / "demo.db"


def weighted_choice(choices: Iterable[Tuple[str, float]]) -> str:
    """Pick a value from (value, weight) pairs."""
    values, weights = zip(*choices)
    return random.choices(values, weights=weights, k=1)[0]


def random_datetime_within(days: int) -> datetime:
    """Return a random datetime within the past `days` days."""
    now = datetime.utcnow()
    delta_days = random.randint(0, days - 1)
    delta_seconds = random.randint(0, 24 * 60 * 60 - 1)
    return now - timedelta(days=delta_days, seconds=delta_seconds)


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    """Return a random datetime between two datetimes."""
    if start >= end:
        return start
    delta = end - start
    total_seconds = int(delta.total_seconds())
    offset = random.randint(0, total_seconds)
    return start + timedelta(seconds=offset)


def fmt(dt: datetime) -> str:
    """Format datetime as naive UTC string without timezone."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def build_users(num_users: int) -> List[Tuple[str, str, str, str, str]]:
    """Generate synthetic users with plausible names and plans."""
    users = []
    for i in range(num_users):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@{random.choice(DOMAINS)}"
        country = random.choice(COUNTRIES)
        plan = weighted_choice(PLANS)
        created_at = fmt(random_datetime_within(DAYS_BACK))
        users.append((name, email, country, plan, created_at))
    return users


def build_payments(user_records: List[sqlite3.Row]) -> List[Tuple[int, float, str, str]]:
    """Generate payment events with realistic statuses and amounts."""
    num_payments = random.randint(PAYMENTS_MIN, PAYMENTS_MAX)
    payments = []
    now = datetime.utcnow()
    for _ in range(num_payments):
        user = random.choice(user_records)
        user_id = user["id"]
        user_plan = user["plan"]
        status = weighted_choice(PAYMENT_STATUSES)
        base_amount = {
            "free": random.uniform(10, 50),
            "pro": random.uniform(30, 150),
            "enterprise": random.uniform(150, 400),
        }.get(user_plan, random.uniform(20, 100))
        amount = round(base_amount * (1.0 if status == "success" else 0.8), 2)
        created_at = fmt(
            random_datetime_between(datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S"), now)
        )
        payments.append((user_id, amount, status, created_at))
    return payments


def build_events(user_records: List[sqlite3.Row]) -> List[Tuple[int, str, str]]:
    """Generate product events per user."""
    events: List[Tuple[int, str, str]] = []
    now = datetime.utcnow()
    for user in user_records:
        user_id = user["id"]
        signup_at = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        events.append((user_id, "signup", fmt(signup_at)))

        # Logins: 1-8 per user distributed after signup
        login_count = random.randint(1, 8)
        for _ in range(login_count):
            login_at = random_datetime_between(signup_at, now)
            events.append((user_id, "login", fmt(login_at)))

        # Checkout only for some users
        if random.random() < 0.4:
            checkout_at = random_datetime_between(signup_at, now)
            events.append((user_id, "checkout", fmt(checkout_at)))

        # Occasional logout to round out event mix
        if random.random() < 0.6:
            logout_at = random_datetime_between(signup_at, now)
            events.append((user_id, "logout", fmt(logout_at)))

    # Trim or pad to fit target range
    target_min = EVENTS_MIN
    target_max = EVENTS_MAX
    if len(events) < target_min:
        extra_needed = target_min - len(events)
        for _ in range(extra_needed):
            u = random.choice(user_records)
            login_at = random_datetime_between(
                datetime.strptime(u["created_at"], "%Y-%m-%d %H:%M:%S"), now
            )
            events.append((u["id"], "login", fmt(login_at)))
    elif len(events) > target_max:
        signup_events = [e for e in events if e[1] == "signup"]
        other_events = [e for e in events if e[1] != "signup"]
        remaining_slots = max(target_max - len(signup_events), 0)
        trimmed = random.sample(other_events, remaining_slots)
        events = signup_events + trimmed
    return events


def build_tickets(user_records: List[sqlite3.Row]) -> List[Tuple[int, str, str, str]]:
    """Generate support tickets for a subset of users."""
    num_tickets = random.randint(TICKETS_MIN, TICKETS_MAX)
    tickets = []
    now = datetime.utcnow()
    for _ in range(num_tickets):
        user = random.choice(user_records)
        user_id = user["id"]
        category = weighted_choice(TICKET_CATEGORIES)
        status = weighted_choice(TICKET_STATUSES)
        created_at = fmt(
            random_datetime_between(
                datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S"), now
            )
        )
        tickets.append((user_id, category, status, created_at))
    return tickets


def create_schema(cursor: sqlite3.Cursor) -> None:
    """Create database schema with foreign keys and indexes."""
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.executescript(
        """
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS tickets;
        DROP TABLE IF EXISTS users;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            country TEXT,
            plan TEXT,
            created_at DATETIME
        );

        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            status TEXT,
            created_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            created_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            status TEXT,
            created_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_payments_user_id ON payments(user_id);
        CREATE INDEX idx_events_user_id ON events(user_id);
        CREATE INDEX idx_tickets_user_id ON tickets(user_id);
        """
    )


def seed() -> None:
    """Create the schema and seed the database with realistic demo data."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.cursor()
        create_schema(cursor)

        users_data = build_users(USERS_TARGET)
        cursor.executemany(
            """
            INSERT INTO users (name, email, country, plan, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            users_data,
        )
        user_records = cursor.execute(
            "SELECT id, name, email, country, plan, created_at FROM users"
        ).fetchall()

        payments_data = build_payments(user_records)
        cursor.executemany(
            """
            INSERT INTO payments (user_id, amount, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            payments_data,
        )

        events_data = build_events(user_records)
        cursor.executemany(
            """
            INSERT INTO events (user_id, name, created_at)
            VALUES (?, ?, ?)
            """,
            events_data,
        )

        tickets_data = build_tickets(user_records)
        cursor.executemany(
            """
            INSERT INTO tickets (user_id, category, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            tickets_data,
        )

        connection.commit()
        print(
            f"Seeded {len(user_records)} users, {len(payments_data)} payments, "
            f"{len(events_data)} events, {len(tickets_data)} tickets."
        )
    finally:
        connection.close()


if __name__ == "__main__":
    random.seed()
    seed()

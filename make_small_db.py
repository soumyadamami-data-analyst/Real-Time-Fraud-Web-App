"""
make_small_db.py
Shrinks the 770 MB fraud_lookup.db to under 24 MB so it can be uploaded
through GitHub's web page (25 MB per-file limit).

Keeps: EVERY fraud row + a sample of legitimate rows.
Transaction IDs are unchanged, so T000... lookups still match the original.
If the result is still over the limit, it halves the legit sample and retries.

Usage (put next to your big fraud_lookup.db):
    python make_small_db.py
Then upload fraud_lookup_small.db to your repo, renamed to fraud_lookup.db.
"""
import os
import sqlite3

SRC = 'fraud_lookup.db'
DST = 'fraud_lookup_small.db'
MAX_MB = 24
keep_every = 100   # keep 1 legit row out of every N; doubles if file is too big

if not os.path.exists(SRC):
    raise SystemExit(f'{SRC} not found. Run this next to your full database.')


def build(keep_every):
    if os.path.exists(DST):
        os.remove(DST)
    conn = sqlite3.connect(DST)
    conn.execute('ATTACH DATABASE ? AS src', (SRC,))
    conn.execute('''
        CREATE TABLE transactions (
            transaction_id TEXT PRIMARY KEY,
            step INTEGER, type TEXT, amount REAL, nameOrig TEXT,
            oldbalanceOrg REAL, newbalanceOrig REAL, nameDest TEXT,
            oldbalanceDest REAL, newbalanceDest REAL,
            isFraud INTEGER, isFlaggedFraud INTEGER
        )
    ''')
    conn.execute('''
        INSERT INTO transactions
        SELECT transaction_id, step, type, amount, nameOrig, oldbalanceOrg,
               newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest,
               isFraud, isFlaggedFraud
        FROM src.transactions
        WHERE isFraud = 1 OR (rowid % ? = 0)
    ''', (keep_every,))
    conn.commit()
    conn.execute('DETACH DATABASE src')
    total = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
    fraud = conn.execute('SELECT COUNT(*) FROM transactions WHERE isFraud = 1').fetchone()[0]
    conn.execute('VACUUM')
    conn.close()
    return total, fraud, os.path.getsize(DST) / 1e6


while True:
    total, fraud, mb = build(keep_every)
    print(f'1-in-{keep_every} legit sample: {total:,} rows ({fraud:,} fraud), {mb:.1f} MB')
    if mb <= MAX_MB:
        break
    keep_every *= 2

print(f'\nDone -> {DST}. Rename it to fraud_lookup.db before uploading.')

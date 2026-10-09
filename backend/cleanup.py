import sqlite3

conn = sqlite3.connect('smart_boe.db')

cur = conn.execute(
    "DELETE FROM verification_results WHERE explanation LIKE '%LLM verification failed%' OR explanation LIKE '%rate-limited%'"
)
conn.commit()
print(f"Deleted {cur.rowcount} failed placeholder rows")

conn.close()
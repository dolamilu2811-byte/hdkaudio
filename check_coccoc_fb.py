import sqlite3, os

temp_db = os.path.join(os.environ['TEMP'], 'coccoc_cookies_export.db')
if not os.path.exists(temp_db):
    print('Temp DB does not exist')
else:
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("SELECT host_key, name, length(value), substr(encrypted_value, 1, 3) FROM cookies WHERE host_key LIKE '%facebook%'")
    rows = c.fetchall()
    print('Facebook cookies count:', len(rows))
    for r in rows:
        print(r)

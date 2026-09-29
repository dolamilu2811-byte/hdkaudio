import os, sqlite3, shutil

coccoc_path = os.path.expandvars(r'%LOCALAPPDATA%\CocCoc\Browser\User Data')
db_path = os.path.join(coccoc_path, 'Default', 'Network', 'Cookies')
temp_db = os.path.join(os.environ['TEMP'], 'coccoc_schema_test.db')
try:
    shutil.copy2(db_path, temp_db)
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM cookies")
    print('Total cookies in Cốc Cốc:', c.fetchone()[0])
    c.execute("SELECT host_key, count(*) FROM cookies WHERE host_key LIKE '%youtube%' OR host_key LIKE '%google%' GROUP BY host_key")
    for r in c.fetchall():
        print(r)
    conn.close()
    if os.path.exists(temp_db):
        os.remove(temp_db)
except Exception as e:
    print('Error:', e)

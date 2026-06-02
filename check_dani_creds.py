import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'athlete.db')
conn = sqlite3.connect(db_path)
row = conn.execute('SELECT email_garmin, password_garmin_enc FROM usuarios WHERE id = 2').fetchone()
if row:
    print(f'Dani email: {row[0]}')
    print(f'Has password: {bool(row[1])}')
else:
    print('Usuario 2 no encontrado')
conn.close()

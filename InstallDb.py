import sqlite3

conn = sqlite3.connect('email.db')
c = conn.cursor()

c.execute('DROP TABLE email;');
c.execute('CREATE TABLE email (id INTEGER PRIMARY KEY AUTOINCREMENT,uuid TEXT NOT NULL,eml TEXT NOT NULL,created_time TIMESTAMP default (datetime(\'now\', \'localtime\')));');

conn.commit()
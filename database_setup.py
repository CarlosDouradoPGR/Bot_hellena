import psycopg2
import os

def create_tables():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            last_interaction TEXT,
            intimacy_level INTEGER DEFAULT 1
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            username TEXT,
            timestamp TEXT,
            role TEXT,
            content TEXT,
            media_sent BOOLEAN DEFAULT FALSE,
            media_url TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Tabelas criadas com sucesso!")

if __name__ == '__main__':
    create_tables()
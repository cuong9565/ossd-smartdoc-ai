import sqlite3
import os
import json

DB_PATH = "smartdoc_ai.sqlite3"

def getConnection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = getConnection() 
    cursor = conn.cursor()
    cursor.execute('''Create table if not exists retriever_state (id Integer primary key autoincrement, session_id text unique, mode text, retriever_k integer, chunk_size integer, chunk_overlap integer, created_at timestamp default current_timestamp)''')

    cursor.execute(
        '''Create table if not exists chat_messages (
            id Integer primary key autoincrement,
            session_id text,
            role text,
            content text,
            response text,
            timestamp text,
            response_time real,
            mode text,
            sources text,
            keywords text
        )'''
    )

    for col_name, col_type in [
        ("timestamp", "text"),
        ("response_time", "real"),
        ("mode", "text"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE chat_messages ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass

    cursor.execute(
        '''create table if not exists document_state(
            id Integer primary key autoincrement,
            session_id text unique,
            file_name text,
            mode text,
            chunk_size integer,
            chunk_overlap integer,
            retriever_k integer,
            documents text,
            documents_json text,
            steps_json text,
            graph_triples_json text,
            created_at timestamp default current_timestamp
        )'''
    )

    try:
        cursor.execute("ALTER TABLE document_state ADD COLUMN documents_json text")
    except sqlite3.OperationalError:
        pass
    for col_name, col_type in [
        ("steps_json", "text"),
        ("graph_triples_json", "text"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE document_state ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

  



import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn_str():
    try:
        with open('api/local.settings.json', 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception as e:
        print(f"Error reading config: {e}")
    return None

def inspect_playlist_items():
    conn_str = get_conn_str()
    if not conn_str:
        return
        
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Find playlist
        cur.execute("SELECT id, name FROM playlists WHERE name LIKE '%Consti%' LIMIT 5")
        playlists = cur.fetchall()
        if not playlists:
            print("No playlist found")
            return
            
        pid = playlists[0]['id']
        print(f"Playlist Name: {playlists[0]['name']}")
        
        # 2. Get items with sort_order
        cur.execute("""
            SELECT id, content_type, content_id, code_id, title, subtitle, sort_order 
            FROM playlist_items 
            WHERE playlist_id = %s 
            ORDER BY sort_order 
            LIMIT 15
        """, (pid,))
        items = cur.fetchall()
        print(f"\n--- ITEMS IN PLAYLIST ({pid}) ---")
        for i in items:
            print(f"Sort: {i['sort_order']} | Title: {i['title']} | ID: {i['content_id']} | Code: {i['code_id']} | Subtitle: {i['subtitle']}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_playlist_items()

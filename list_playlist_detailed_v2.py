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
         pass
    return None

def list_playlist():
    conn_str = get_conn_str()
    if not conn_str: 
        print("DB_CONNECTION_STRING not found")
        return
    
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT id, name FROM playlists WHERE name LIKE '%Consti%' LIMIT 5")
        playlists = cur.fetchall()
        if not playlists: 
            print("No playlist found with name containing 'Consti'")
            return
        
        pid = playlists[0]['id']
        print(f"Playlist: {playlists[0]['name']} (ID: {pid})")
        
        # Get up to 50 items to see the flow
        cur.execute("""
            SELECT sort_order, title, content_id, code_id 
            FROM playlist_items 
            WHERE playlist_id = %s 
            ORDER BY sort_order 
            LIMIT 50
        """, (pid,))
        items = cur.fetchall()
        for i in items:
             print(f"[{i['sort_order']}] {i['title']} - ID: {i['content_id']} ({i['code_id']})")
             
        cur.close()
        conn.close()
    except Exception as e:
         print(f"Error: {e}")

if __name__ == "__main__":
    list_playlist()

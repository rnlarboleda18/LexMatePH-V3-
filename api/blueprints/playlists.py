import azure.functions as func
import json
import os
import logging
import traceback
from db_pool import get_db_connection, put_db_connection
from utils.clerk_auth import get_authenticated_user_id

playlists_bp = func.Blueprint()

@playlists_bp.route(route="playlists", methods=["GET"])
def get_playlists(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at FROM playlists WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        rows = cur.fetchall()
        playlists = [{"id": str(r[0]), "name": r[1], "created_at": r[2].isoformat()} for r in rows]
        
        # Fetch item counts
        if playlists:
            playlist_ids = [p["id"] for p in playlists]
            cur.execute("SELECT playlist_id, count(*) FROM playlist_items WHERE playlist_id::text = ANY(%s) GROUP BY playlist_id", (playlist_ids,))
            counts = dict((str(r[0]), r[1]) for r in cur.fetchall())
            for p in playlists:
                p["item_count"] = counts.get(p["id"], 0)
                        
        return func.HttpResponse(json.dumps(playlists), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error fetching playlists: {traceback.format_exc()}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass

@playlists_bp.route(route="playlists", methods=["POST"])
def create_playlist(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    
    req_body = req.get_json()
    name = req_body.get("name")
    if not name: return func.HttpResponse(json.dumps({"error": "Name required"}), status_code=400)
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO playlists (user_id, name) VALUES (%s, %s) RETURNING id, name, created_at", (user_id, name))
        r = cur.fetchone()
        playlist = {"id": str(r[0]), "name": r[1], "created_at": r[2].isoformat(), "item_count": 0}
        conn.commit()
        return func.HttpResponse(json.dumps(playlist), mimetype="application/json", status_code=201)
    except Exception as e:
        logging.error(f"Error creating playlist: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

@playlists_bp.route(route="playlists/{playlist_id}", methods=["PUT"])
def rename_playlist(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    
    playlist_id = req.route_params.get('playlist_id')
    req_body = req.get_json()
    name = req_body.get("name")
    if not name: return func.HttpResponse(json.dumps({"error": "Name required"}), status_code=400)
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE playlists SET name = %s WHERE id = %s AND user_id = %s RETURNING id", (name, playlist_id, user_id))
        if not cur.fetchone():
            return func.HttpResponse(json.dumps({"error": "Not found or unauthorized"}), status_code=404)
        conn.commit()
        return func.HttpResponse(json.dumps({"success": True}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error renaming playlist: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

@playlists_bp.route(route="playlists/{playlist_id}", methods=["DELETE"])
def delete_playlist(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    
    playlist_id = req.route_params.get('playlist_id')
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM playlists WHERE id = %s AND user_id = %s RETURNING id", (playlist_id, user_id))
        if not cur.fetchone():
            return func.HttpResponse(json.dumps({"error": "Not found or unauthorized"}), status_code=404)
        conn.commit()
        return func.HttpResponse(json.dumps({"success": True}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error deleting playlist: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

@playlists_bp.route(route="playlists/{playlist_id}/items", methods=["GET"])
def get_playlist_items(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    playlist_id = req.route_params.get('playlist_id')
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Verify ownership and fetch items in one block
        cur.execute("""
            SELECT id, content_id, content_type, code_id, title, subtitle, sort_order 
            FROM playlist_items 
            WHERE playlist_id = %s 
              AND playlist_id IN (SELECT id FROM playlists WHERE user_id = %s)
            ORDER BY sort_order ASC
        """, (playlist_id, user_id))
        
        rows = cur.fetchall()
        items = [{
            "playlist_item_id": r[0],
            "id": r[1],
            "type": r[2],
            "code_id": r[3],
            "title": r[4],
            "subtitle": r[5],
            "sort_order": r[6]
        } for r in rows]
        return func.HttpResponse(json.dumps(items), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error fetching items: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

@playlists_bp.route(route="playlists/{playlist_id}/items", methods=["POST"])
def add_playlist_item(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    playlist_id = req.route_params.get('playlist_id')
    
    req_body = req.get_json()
    c_id = req_body.get("content_id")
    c_type = req_body.get("content_type")
    
    if not c_id or not c_type: return func.HttpResponse(json.dumps({"error": "content_id and content_type required"}), status_code=400)
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Verify ownership and get max sort_order
        cur.execute("SELECT id FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id))
        if not cur.fetchone(): return func.HttpResponse(json.dumps({"error": "Not found"}), status_code=404)
        
        cur.execute("SELECT COALESCE(MAX(sort_order), 0) FROM playlist_items WHERE playlist_id = %s", (playlist_id,))
        next_order = cur.fetchone()[0] + 1
        
        cur.execute("""
            INSERT INTO playlist_items (playlist_id, content_id, content_type, code_id, title, subtitle, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (playlist_id, str(c_id), c_type, req_body.get('code_id'), req_body.get('title'), req_body.get('subtitle'), next_order))
        new_id = cur.fetchone()[0]
        conn.commit()
                
        item = {
            "playlist_item_id": new_id,
            "id": str(c_id),
            "type": c_type,
            "code_id": req_body.get('code_id'),
            "title": req_body.get('title'),
            "subtitle": req_body.get('subtitle'),
            "sort_order": next_order
        }
        return func.HttpResponse(json.dumps(item), mimetype="application/json", status_code=201)
    except Exception as e:
        logging.error(f"Error adding item: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

@playlists_bp.route(route="playlists/{playlist_id}/items/{item_id}", methods=["DELETE"])
def remove_playlist_item(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    playlist_id = req.route_params.get('playlist_id')
    item_id = req.route_params.get('item_id')
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM playlist_items WHERE id = %s AND playlist_id IN (SELECT id FROM playlists WHERE id = %s AND user_id = %s) RETURNING id", (item_id, playlist_id, user_id))
        if not cur.fetchone(): return func.HttpResponse(json.dumps({"error": "Item not found or unauthorized"}), status_code=404)
        conn.commit()
        return func.HttpResponse(json.dumps({"success": True}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error removing item: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

@playlists_bp.route(route="playlists/{playlist_id}/bulk_items", methods=["POST"])
def add_playlist_items_bulk(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    playlist_id = req.route_params.get('playlist_id')
    
    req_body = req.get_json()
    items_to_add = req_body.get("items", [])
    if not items_to_add: return func.HttpResponse(json.dumps({"error": "No items provided"}), status_code=400)
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Verify ownership
        cur.execute("SELECT id FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id))
        if not cur.fetchone(): return func.HttpResponse(json.dumps({"error": "Not found"}), status_code=404)
        
        # Get starting sort_order
        cur.execute("SELECT COALESCE(MAX(sort_order), 0) FROM playlist_items WHERE playlist_id = %s", (playlist_id,))
        start_order = cur.fetchone()[0] + 1
        
        # Prepare bulk values
        values = []
        for i, item in enumerate(items_to_add):
            c_id = item.get("content_id")
            c_type = item.get("content_type")
            if not c_id or not c_type: continue
            
            values.append((
                playlist_id, 
                str(c_id), 
                c_type, 
                item.get('code_id'), 
                item.get('title'), 
                item.get('subtitle'), 
                start_order + i
            ))
        
        if values:
            # Multi-row INSERT
            placeholders = ",".join(["(%s,%s,%s,%s,%s,%s,%s)"] * len(values))
            cur.execute(f"""
                INSERT INTO playlist_items (playlist_id, content_id, content_type, code_id, title, subtitle, sort_order)
                VALUES {placeholders} RETURNING id
            """, [val for sublist in values for val in sublist])
            
            ids = [r[0] for r in cur.fetchall()]
            conn.commit()
            
            # Reconstruct items for response
            response_items = []
            for i, item in enumerate(items_to_add):
                 response_items.append({**item, "playlist_item_id": ids[i] if i < len(ids) else None, "sort_order": start_order + i})
            
            return func.HttpResponse(json.dumps(response_items), mimetype="application/json", status_code=201)
        
        return func.HttpResponse(json.dumps([]), mimetype="application/json")
    except Exception as e:
        logging.error(f"Error bulk adding items: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)

@playlists_bp.route(route="lexplay/state", methods=["GET"])
def get_playback_state(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT playlist_id, current_track_id, "current_time", playback_rate 
            FROM user_playback_state WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        if row:
            state = {
                "playlist_id": str(row[0]) if row[0] else None,
                "current_track_id": row[1],
                "current_time": float(row[2]),
                "playback_rate": float(row[3])
            }
            return func.HttpResponse(json.dumps(state), mimetype="application/json", status_code=200)
        else:
            return func.HttpResponse(json.dumps({}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error fetching playback state: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if cur: cur.close()
        if conn: put_db_connection(conn)

@playlists_bp.route(route="lexplay/state", methods=["POST"])
def save_playback_state(req: func.HttpRequest) -> func.HttpResponse:
    user_id, auth_error = get_authenticated_user_id(req)
    if not user_id: return func.HttpResponse(json.dumps({"error": "Unauthorized", "details": auth_error}), status_code=401)
    
    conn = None
    cur = None
    try:
        req_body = req.get_json()
        p_id = req_body.get("playlist_id")
        t_id = req_body.get("current_track_id")
        c_time = req_body.get("current_time", 0)
        p_rate = req_body.get("playback_rate", 1.0)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_playback_state (user_id, playlist_id, current_track_id, "current_time", playback_rate, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                playlist_id = EXCLUDED.playlist_id,
                current_track_id = EXCLUDED.current_track_id,
                "current_time" = EXCLUDED."current_time",
                playback_rate = EXCLUDED.playback_rate,
                updated_at = NOW()
        """, (user_id, p_id, t_id, c_time, p_rate))
        conn.commit()
        return func.HttpResponse(json.dumps({"success": True}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error saving playback state: {e}")
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500)
    finally:
        if cur: cur.close()
        if conn: put_db_connection(conn)

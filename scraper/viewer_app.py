import streamlit as st
import os
import json
import re

# Configuration
DOWNLOADS_DIR = "downloads"

st.set_page_config(layout="wide", page_title="SC Decision Viewer")

st.title("🇵🇭 Supreme Court Decision Viewer")

# --- Helper Functions ---
def get_years():
    if not os.path.exists(DOWNLOADS_DIR):
        return []
    years = [d for d in os.listdir(DOWNLOADS_DIR) if d.isdigit()]
    return sorted(years, reverse=True)

def get_files_in_dir(path):
    if not os.path.exists(path):
        return []
    return [f for f in os.listdir(path) if f.endswith(".json")]

def get_months(year):
    year_path = os.path.join(DOWNLOADS_DIR, year)
    if not os.path.exists(year_path):
        return []
    # Get all directories
    all_dirs = [d for d in os.listdir(year_path) if os.path.isdir(os.path.join(year_path, d))]
    
    # Filter: Only keep months that have JSON files
    valid_months = []
    for d in all_dirs:
        if get_files_in_dir(os.path.join(year_path, d)):
            valid_months.append(d)
            
    return sorted(valid_months)

def get_files(year, month):
    month_path = os.path.join(DOWNLOADS_DIR, year, month)
    files = get_files_in_dir(month_path)
    
    # Try to sort numerically if possible (filenames are usually 1.json, 2.json etc)
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
    
    return sorted(files, key=natural_sort_key)

def load_case(year, month, filename):
    path = os.path.join(DOWNLOADS_DIR, year, month, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- Sidebar ---
st.sidebar.header("Navigation")

# Search Mode Toggle
search_mode = st.sidebar.checkbox("🔍 Search Mode")

if search_mode:
    query = st.sidebar.text_input("Enter keyword (e.g., 'dissenting', 'G.R. No.')")
    if query:
        st.sidebar.write("Searching... (this might take a moment)")
        # Simple walk search (could be slow for 66k files, so maybe limit scope or just warn)
        # For a quick hack, let's just search the current year if selected, or just simple match
        # Actually better to keep it simple: Search by File ID or G.R. Number matching in the current year?
        # Let's just implement a simple Year-scope search for speed.
        
        years = get_years()
        search_year = st.sidebar.selectbox("Year to Search", years, index=0)
        
        results = []
        year_path = os.path.join(DOWNLOADS_DIR, search_year)
        if os.path.exists(year_path):
            for month in os.listdir(year_path):
                m_path = os.path.join(year_path, month)
                if os.path.isdir(m_path):
                    for f in os.listdir(m_path):
                        if f.endswith(".json"):
                            # Lazy check: read file? Reading all 1000 files is okay.
                            # But reading 60k is bad.
                            # Just filename search?
                            if query.lower() in f.lower(): # Search by filename/ID
                                results.append((search_year, month, f))
                                continue
                                
                            # If they want content search, we need to read. 
                            # Let's only read if query is > 3 chars
                            if len(query) > 3:
                                try:
                                    with open(os.path.join(m_path, f), 'r', encoding='utf-8') as jf:
                                        c = json.load(jf)
                                        # Search in Case Number or Main Text
                                        if query.lower() in c.get('case_number', '').lower() or query.lower() in c.get('main_text', '')[:1000].lower():
                                            results.append((search_year, month, f))
                                except:
                                    pass
        
        if results:
            sel_res = st.sidebar.selectbox("Search Results", results, format_func=lambda x: f"{x[1]}/{x[2]}")
            if sel_res:
                selected_year, selected_month, selected_file = sel_res
        else:
            st.sidebar.warning("No matches found in this year.")
            selected_file = None

else:
    # Browse Mode
    years = get_years()
    if not years:
        st.error("No data found in downloads directory.")
        st.stop()

    selected_year = st.sidebar.selectbox("Year", years)

    months = get_months(selected_year)
    if not months:
        st.sidebar.warning(f"No data for {selected_year}")
        selected_month = None
    else:
        selected_month = st.sidebar.selectbox("Month", months)

    if selected_month:
        files = get_files(selected_year, selected_month)
        selected_file = st.sidebar.selectbox("Case File", files)
    else:
        selected_file = None

# --- Main Content ---
if 'selected_file' in locals() and selected_file:
    data = load_case(selected_year, selected_month, selected_file)
    
    st.subheader(f"Case: {data.get('case_number', 'Unknown Case Number')}")
    st.caption(f"File: {selected_file} | Year: {data.get('year')}")
    st.divider()
    
    main_text = data.get("main_text", "")
    
    # Highlight Opinions
    # We will do simple string replacement to add bold/color to specific headers
    # Streamlit supports markdown.
    
    markers = ["DISSENTING OPINION", "CONCURRING OPINION", "SEPARATE OPINION", "CONCURRING AND DISSENTING OPINION"]
    
    formatted_text = main_text
    
    for marker in markers:
        # Regex to find the marker (case insensitive) and make it red/bold
        # We use re.sub with a function to preserve case if we wanted, but standardizing is fine.
        # Let's make it Red and H3
        pattern = re.compile(re.escape(marker), re.IGNORECASE)
        replacement = f"### :red[{marker}]"
        formatted_text = pattern.sub(replacement, formatted_text)
        
    st.markdown(formatted_text)

else:
    st.info("Select a case to view.")

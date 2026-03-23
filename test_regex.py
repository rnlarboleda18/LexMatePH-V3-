import re

def is_topic_header(line):
    # Ignore Q: and A: lines
    if re.match(r'^(Q|Q\.|Question|A|A\.|Answer)\s*:', line, re.IGNORECASE):
        return False
        
    # Check if the line matches the topic header pattern:
    # Optional numbering: 1., a., A., II., etc.
    # Followed by strictly uppercase text, numbers, and basic punctuation
    # Optionally ending with a BAR year list: (2022, 2020-21... BAR)
    
    # Let's break it down:
    # Numbering: ^([A-Za-z0-9IVX]+\.)?\s*
    # Body: [A-Z0-9\s,\.\-\(\)&/]+   <- ONLY allow uppercase, no lowercase!
    # The whole line must match this.
    
    # Wait, the body might contain the BAR string inside it because of the uppercase requirement
    pattern = r'^([A-Za-z0-9IVX]+\.)?\s*[A-Z0-9\s,\.\-\(\)&/]+$'
    
    if re.match(pattern, line):
        return True
    return False

test_lines = [
    "2. CIRCUMSTANCES AFFECTING CRIMINAL LIABILITY (2022, 2020-21, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012, 2011, 2010, 2009, 2008, 2005, 2004, 2003, 2002, 2001, 2000, 1999, 1998, 1997, 1996, 1995, 1994, 1993, 1992, 1991, 1990, 1989, 1988, 1987 BAR)",
    "a. JUSTIFYING CIRCUMSTANCES ART. 11, RPC (2022, 2019, 2017, 2016, 2015, 2014, 2012, 2011, 2010, 2009, 2008, 2004, 2003, 2002, 2001, 2000, 1998, 1996, 1993, 1992, 1990, 1989, 1987 BAR)",
    "II. MARRIAGE",
    "E. WAIVER OF RIGHTS",
    "J. HUMAN RELATIONS IN RELATION TO PERSONS (2022, 2020-21, 2014, 2011, 1996 BAR)",
    "A: YES. Baby can file for annulment.",
    "Q: What is the rule?",
    "FALSE. Marsha is not estopped...",
    "Under Art. 296 of RPC, any member of a band",
    "BIGAMOUS OR POLYGAMOUS MARRIAGES (2017, 2008, 2005, 1993, 1991 BAR)"
]

for l in test_lines:
    print(f"[{'MATCH' if is_topic_header(l) else 'NO MATCH'}] {l[:50]}...")

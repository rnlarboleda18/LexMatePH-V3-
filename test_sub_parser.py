import re

def parse_subquestions(q_idx, raw_q, raw_a):
    """
    Given the raw Q and A text for a single problem,
    extracts the main narrative and the sub-questions/answers.
    """
    # Fix common typo where Answer gets glued to question in same block
    
    # 1. Combine them into one text to make it easier to search, 
    # BUT we need to be careful if (a) is in both Q and A.
    combined = raw_q + " " + raw_a
    
    # Let's find all occurrences of (a), (b), (c), etc. or a., b., c.
    # We will only look for (a), (b), (c) ... (e) for now, as that's standard
    
    sub_q_pattern = re.compile(r'\(([a-g])\)\s+(.*?)(?=\([a-g]\)\s+|A:|$)')
    
    # Wait, the problem is 'A:' can mark the answer to a subquestion,
    # or the start of the main answer.
    
    # Let's write a parser that tokenizes the text into a stream of tags:
    # TEXT, SUB_MARKER, A_MARKER
    
    # Instead of regex all at once, let's split by A: and (a), (b), etc.
    # regex to split keeping the delimiters
    tokens = re.split(r'(\([a-g]\)|A:)', combined)
    
    # Remove empty tokens
    tokens = [t.strip() for t in tokens if t.strip()]
    
    main_narrative = ""
    sub_pairs = []
    
    current_sub = None
    current_mode = "MAIN_NARRATIVE"
    
    current_q_buf = []
    current_a_buf = []
    
    for t in tokens:
        if re.match(r'\([a-g]\)', t):
            # We hit a sub-question (a), (b), etc.
            # Save the previous sub-question if any
            if current_sub:
                sub_pairs.append({
                    "sub": current_sub,
                    "q": " ".join(current_q_buf),
                    "a": " ".join(current_a_buf)
                })
            else:
                # We are leaving the main narrative
                main_narrative = " ".join(current_q_buf)
                
            current_sub = t.strip('()')
            current_q_buf = []
            current_a_buf = []
            current_mode = "Q"
            
        elif t == "A:":
            # We hit an answer marker
            current_mode = "A"
        else:
            if current_mode == "MAIN_NARRATIVE":
                current_q_buf.append(t)
            elif current_mode == "Q":
                current_q_buf.append(t)
            elif current_mode == "A":
                current_a_buf.append(t)
                
    # append the last one
    if current_sub:
        sub_pairs.append({
            "sub": current_sub,
            "q": " ".join(current_q_buf).strip(),
            "a": " ".join(current_a_buf).strip()
        })
    else:
        # No sub questions found
        main_narrative = raw_q
        # raw_a might start with A:, so let's clean it
        clean_a = re.sub(r'^A:\s*', '', raw_a).strip()
    
    output = []
    if main_narrative.startswith('Q:'):
        main_narrative = main_narrative[2:].strip()
        
    output.append(f"Q{q_idx}: {main_narrative}\n")
    
    if not sub_pairs:
        output.append(f"A{q_idx}: {clean_a}\n")
    else:
        for pair in sub_pairs:
            output.append(f"Q{q_idx}{pair['sub']}: {pair['q']}")
            if pair['a']:
                output.append(f"A{q_idx}{pair['sub']}: {pair['a']}\n")
            else:
                output.append(f"A{q_idx}{pair['sub']}: \n")
                
    return "\n".join(output)

# Test with Q44 text
q_text = "Q: Pedro, Pablito, Juan, and Julio, all armed with bolos, robbed the house where Antonio, his wife, and three (3) daughters were residing. While the four were ransacking Antonio's house, Julio noticed that one of Antonio's daughters was trying to escape. He chased and caught up with her at a thicket somewhat distant from the house, but before bringing her back, raped her. (2016 BAR) (a) What crime or crimes, if any, did Pedro, Pablito, Juan, and Julio commit? Explain."

a_text = "A: Julio is liable for special complex crime of robbery with rape since he had carnal knowledge of Antonio’s daughter on occasion or by reason of robbery. Even if the place of robbery is different from that of rape, what is important is the direct connection between the crimes (People v. Canastre, G.R. No. L-2055, 24 Dec. 1948). Rape was not separate by distance and time from the robbery. Pedro, Pablito, and Juan are liable for robbery by a band. There is a band in this case since more than three armed malefactors took part in the commission of robbery. Under Art. 296 of RPC, any member of a band, who is present at the commission of a robbery by a band, shall be punished as principal of any of the assaults committed by the band, unless it be shown that he attempted to prevent the same. The assault mentioned in Art. 296 includes rape. (People v. Hamiana, G.R. Nos. L-39491-94, 30 May 1971) They are not liable, however, for rape since they were not present when the victim was raped and thus, they had no opportunity to prevent the same. They are only liable for robbery by band. (People v. Anticamaray, G.R. No. 178771, 08 June 2011) (b) Suppose, after the robbery, the four took turns in raping the three daughters inside the house, and, to prevent identification, killed the whole family just before they left. What crime or crimes, if any, did the four malefactors commit? A: They are liable for special complex crime of robbery with homicide. In this special complex crime, it is immaterial that several persons are killed. It is also immaterial that aside from the homicides, rapes are committed by reason or on the occasion of the crime. Since homicides are committed by or on the occasion of the robbery, the multiple rapes shall be integrated into one and indivisible felony of robbery with homicide. (People v. Diu, G.R. No. 201449, 03 Apr. 2013) (UPLC Suggested Answers)"

print(parse_subquestions(44, q_text, a_text))

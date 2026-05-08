"""
Criminal Law — 2026 Bar Syllabus Topic-to-Provision Map
Case cutoff: June 30, 2025

source='db'     → provision is in rpc_codal; fetched directly from DB
source='scrape' → provision scraped from LawPhil (primary), SC eLib (fallback)
source='ai'     → no codal text available; AI synthesizes from case law

LawPhil URL patterns:
  RA  → https://lawphil.net/statutes/repacts/ra{yr}/ra_{num}_{yr}.html
  PD  → https://lawphil.net/statutes/presdecs/pd{yr}/pd_{num}_{yr}.html
  BP  → https://lawphil.net/statutes/bpblg/bp_{num}_{yr}.html
  CA  → https://lawphil.net/statutes/comacts/ca_{num}_{yr}.html
  Act → https://lawphil.net/statutes/acts/act_{num}.html

SC eLib fallback:
  RA  → https://elibrary.judiciary.gov.ph/republic_acts/{num}
"""

LAWPHIL = "https://lawphil.net"
ELIB    = "https://elibrary.judiciary.gov.ph"

CRIMINAL_MAP = [

    # ──────────────────────────────────────────────────────────────────────────
    # I. FUNDAMENTAL PRINCIPLES
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "I", "topic_heading": "Fundamental Principles",
        "sub_letter": "A", "sub_heading": "Construction or Interpretation of Penal Laws",
        "sort_order": 1,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "1",  "label": "Art. 1 – Time when Act takes effect", "source": "db"},
            {"statute_id": "RPC", "provision_id": "2",  "label": "Art. 2 – Application of penal laws", "source": "db"},
            {"statute_id": "RPC", "provision_id": "10", "label": "Art. 10 – Offenses not subject to RPC; suppletory application", "source": "db"},
            {"statute_id": "RPC", "provision_id": "22", "label": "Art. 22 – Retroactive effect of penal laws", "source": "db"},
        ]
    },
    {
        "roman_num": "I", "topic_heading": "Fundamental Principles",
        "sub_letter": "B", "sub_heading": "Nullum Crimen, Nulla Poena Sine Lege",
        "sort_order": 2,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "1", "label": "Art. 1 – No crime without law", "source": "db"},
            {"statute_id": "RPC", "provision_id": "21", "label": "Art. 21 – No felony without a law penalizing it", "source": "db"},
        ]
    },
    {
        "roman_num": "I", "topic_heading": "Fundamental Principles",
        "sub_letter": "C", "sub_heading": "Mala In Se and Mala Prohibita",
        "sort_order": 3,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "3",  "label": "Art. 3 – Felonies (dolo vs culpa)", "source": "db"},
            {"statute_id": "RPC", "provision_id": "10", "label": "Art. 10 – Suppletory application to special laws", "source": "db"},
        ]
    },
    {
        "roman_num": "I", "topic_heading": "Fundamental Principles",
        "sub_letter": "D", "sub_heading": "Cardinal Principles (Generality, Territoriality, Prospectivity)",
        "sort_order": 4,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "2",  "label": "Art. 2 – Territoriality and exceptions", "source": "db"},
            {"statute_id": "RPC", "provision_id": "22", "label": "Art. 22 – Prospectivity; retroactive effect when favorable", "source": "db"},
        ]
    },
    {
        "roman_num": "I", "topic_heading": "Fundamental Principles",
        "sub_letter": "E", "sub_heading": "Constitutional Limitations on the Power to Enact Penal Laws",
        "sort_order": 5,
        "provisions": [
            # Constitutional provisions — in consti_codal
            {"statute_id": "CONST", "provision_id": "III-1",  "label": "Art. III, Sec. 1 – Due Process and Equal Protection", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-19", "label": "Art. III, Sec. 19 – Prohibition on excessive fines and cruel punishment", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-22", "label": "Art. III, Sec. 22 – Ex post facto laws and bills of attainder", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # II. FELONIES AND CRIMINAL LIABILITY
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "II", "topic_heading": "Felonies and Criminal Liability",
        "sub_letter": "A", "sub_heading": "Felonies — Definition, Dolo/Culpa, Stages, Plurality",
        "sort_order": 6,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "3",  "label": "Art. 3 – Felonies defined; dolo and culpa", "source": "db"},
            {"statute_id": "RPC", "provision_id": "4",  "label": "Art. 4 – Criminal liability; proximate cause", "source": "db"},
            {"statute_id": "RPC", "provision_id": "6",  "label": "Art. 6 – Stages of execution (consummated, frustrated, attempted)", "source": "db"},
            {"statute_id": "RPC", "provision_id": "7",  "label": "Art. 7 – When light felonies are punishable", "source": "db"},
            {"statute_id": "RPC", "provision_id": "48", "label": "Art. 48 – Complex crimes (compound and complex proper)", "source": "db"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Felonies and Criminal Liability",
        "sub_letter": "B", "sub_heading": "Criminal Liability — Actus Reus, Mens Rea, Participation, Circumstances",
        "sort_order": 7,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "4",  "label": "Art. 4 – Criminal liability", "source": "db"},
            {"statute_id": "RPC", "provision_id": "5",  "label": "Art. 5 – Duty of courts when act not punishable or penalty excessive", "source": "db"},
            {"statute_id": "RPC", "provision_id": "8",  "label": "Art. 8 – Conspiracy and proposal to commit a felony", "source": "db"},
            {"statute_id": "RPC", "provision_id": "11", "label": "Art. 11 – Justifying circumstances", "source": "db"},
            {"statute_id": "RPC", "provision_id": "12", "label": "Art. 12 – Exempting circumstances", "source": "db"},
            {"statute_id": "RPC", "provision_id": "13", "label": "Art. 13 – Mitigating circumstances", "source": "db"},
            {"statute_id": "RPC", "provision_id": "14", "label": "Art. 14 – Aggravating circumstances", "source": "db"},
            {"statute_id": "RPC", "provision_id": "15", "label": "Art. 15 – Alternative circumstances", "source": "db"},
            {"statute_id": "RPC", "provision_id": "16", "label": "Art. 16 – Persons criminally liable", "source": "db"},
            {"statute_id": "RPC", "provision_id": "17", "label": "Art. 17 – Principals", "source": "db"},
            {"statute_id": "RPC", "provision_id": "18", "label": "Art. 18 – Accomplices", "source": "db"},
            {"statute_id": "RPC", "provision_id": "19", "label": "Art. 19 – Accessories", "source": "db"},
            # Special laws cited in II-B
            {"statute_id": "RA-9344", "provision_id": "6",
             "label": "R.A. 9344, Sec. 6 – Minimum age of criminal responsibility (Juvenile Justice)", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2006/ra_9344_2006.html",
             "specific_sections": "Sec. 6"},
            {"statute_id": "RA-9262", "provision_id": "general",
             "label": "R.A. 9262 – Battered Woman Syndrome as exempting circumstance", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2004/ra_9262_2004.html",
             "specific_sections": "Sec. 26"},
            {"statute_id": "RA-10591", "provision_id": "29",
             "label": "R.A. 10591, Sec. 29 – Using loose firearm as aggravating circumstance", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2013/ra_10591_2013.html",
             "specific_sections": "Sec. 29"},
            {"statute_id": "RA-9165", "provision_id": "25",
             "label": "R.A. 9165, Sec. 25 – Influence of dangerous drugs as aggravating circumstance", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2002/ra_9165_2002.html",
             "specific_sections": "Sec. 25"},
            {"statute_id": "RA-10175", "provision_id": "6",
             "label": "R.A. 10175, Sec. 6 – ICT as aggravating circumstance", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2012/ra_10175_2012.html",
             "specific_sections": "Sec. 6"},
            {"statute_id": "PD-1612", "provision_id": "general",
             "label": "P.D. 1612 – Fencing; accessories in property crimes", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1979/pd_1612_1979.html"},
            {"statute_id": "PD-1829", "provision_id": "general",
             "label": "P.D. 1829 – Obstruction of criminal prosecution", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1981/pd_1829_1981.html"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Felonies and Criminal Liability",
        "sub_letter": "C", "sub_heading": "Penalties — Classification, Application, Execution, and Service",
        "sort_order": 8,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "21", "label": "Art. 21 – Penalties; no felony without a law", "source": "db"},
            {"statute_id": "RPC", "provision_id": "25", "label": "Art. 25 – Classification of penalties", "source": "db"},
            {"statute_id": "RPC", "provision_id": "27", "label": "Art. 27 – Reclusion perpetua", "source": "db"},
            {"statute_id": "RPC", "provision_id": "29", "label": "Art. 29 – Preventive imprisonment", "source": "db"},
            {"statute_id": "RPC", "provision_id": "36", "label": "Art. 36 – Pardon; effects", "source": "db"},
            {"statute_id": "RPC", "provision_id": "39", "label": "Art. 39 – Subsidiary penalty", "source": "db"},
            {"statute_id": "RPC", "provision_id": "47", "label": "Art. 47 – Three-fold rule / successive service", "source": "db"},
            {"statute_id": "RPC", "provision_id": "63", "label": "Art. 63 – Rules for application of indivisible penalties", "source": "db"},
            {"statute_id": "RPC", "provision_id": "64", "label": "Art. 64 – Rules for divisible penalties with mitigating/aggravating", "source": "db"},
            # Special penalty laws
            {"statute_id": "ACT-4103", "provision_id": "general",
             "label": "Act No. 4103 – Indeterminate Sentence Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/acts/act_4103.html"},
            {"statute_id": "PD-968", "provision_id": "general",
             "label": "P.D. 968 – Probation Law, as amended", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1976/pd_968_1976.html"},
            {"statute_id": "RA-10389", "provision_id": "general",
             "label": "R.A. 10389 – Recognizance Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2013/ra_10389_2013.html"},
            {"statute_id": "RA-11362", "provision_id": "general",
             "label": "R.A. 11362 – Community Service Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2019/ra_11362_2019.html"},
            {"statute_id": "RA-10592", "provision_id": "general",
             "label": "R.A. 10592 – Good Conduct Time Allowance (GCTA)", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2013/ra_10592_2013.html"},
            {"statute_id": "RA-9344", "provision_id": "general",
             "label": "R.A. 9344 – Juvenile Justice and Welfare Act (criminal liability of minors)", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2006/ra_9344_2006.html",
             "specific_sections": "Secs. 6, 57-58"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Felonies and Criminal Liability",
        "sub_letter": "D", "sub_heading": "Extinction of Criminal Liability",
        "sort_order": 9,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "89", "label": "Art. 89 – How criminal liability is totally extinguished", "source": "db"},
            {"statute_id": "RPC", "provision_id": "90", "label": "Art. 90 – Prescription of crimes", "source": "db"},
            {"statute_id": "RPC", "provision_id": "91", "label": "Art. 91 – Computation of prescription of offenses", "source": "db"},
            {"statute_id": "RPC", "provision_id": "92", "label": "Art. 92 – Prescription of penalties", "source": "db"},
            {"statute_id": "RPC", "provision_id": "94", "label": "Art. 94 – Partial extinction of criminal liability", "source": "db"},
            {"statute_id": "ACT-3326", "provision_id": "general",
             "label": "Act No. 3326 – Prescription of offenses under special laws", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/acts/act_3326.html"},
            {"statute_id": "RA-10592", "provision_id": "general",
             "label": "R.A. 10592 – GCTA; partial extinction", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2013/ra_10592_2013.html"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Felonies and Criminal Liability",
        "sub_letter": "E", "sub_heading": "Civil Liability Ex Delicto",
        "sort_order": 10,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "100", "label": "Art. 100 – Civil liability of persons guilty of felony", "source": "db"},
            {"statute_id": "RPC", "provision_id": "101", "label": "Art. 101 – Rules on civil liability when felony not punishable", "source": "db"},
            {"statute_id": "RPC", "provision_id": "102", "label": "Art. 102 – Subsidiary civil liability of innkeepers and tavern-keepers", "source": "db"},
            {"statute_id": "RPC", "provision_id": "103", "label": "Art. 103 – Subsidiary civil liability of employers", "source": "db"},
            {"statute_id": "RPC", "provision_id": "104", "label": "Art. 104 – What civil liability includes", "source": "db"},
            {"statute_id": "RPC", "provision_id": "112", "label": "Art. 112 – Extinction of civil liability", "source": "db"},
            {"statute_id": "RPC", "provision_id": "113", "label": "Art. 113 – Obligation to satisfy civil liability", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # III. CRIMES AND THEIR PENALTIES
    # ──────────────────────────────────────────────────────────────────────────

    # A — National Security
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "A", "sub_heading": "Title One – Crimes against National Security and Law of Nations",
        "sort_order": 11,
        "provisions": [
            {"statute_id": "PD-532", "provision_id": "general",
             "label": "P.D. 532 – Anti-Piracy and Anti-Highway Robbery Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1974/pd_532_1974.html"},
            {"statute_id": "RA-11479", "provision_id": "general",
             "label": "R.A. 11479 – Anti-Terrorism Act of 2020", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2020/ra_11479_2020.html"},
            {"statute_id": "RA-10168", "provision_id": "general",
             "label": "R.A. 10168 – Terrorism Financing Prevention and Suppression Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2012/ra_10168_2012.html"},
            {"statute_id": "RA-9851", "provision_id": "4-5",
             "label": "R.A. 9851, Secs. 4 & 5 – Philippine Act on Crimes Against International Humanitarian Law (Genocide, War Crimes)", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2009/ra_9851_2009.html",
             "specific_sections": "Secs. 4, 5"},
        ]
    },

    # B — Fundamental Laws
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "B", "sub_heading": "Title Two – Crimes against the Fundamental Laws of the State",
        "sort_order": 12,
        "provisions": [
            {"statute_id": "RA-9745", "provision_id": "general",
             "label": "R.A. 9745 – Anti-Torture Act of 2009", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2009/ra_9745_2009.html"},
            {"statute_id": "RA-9851", "provision_id": "6",
             "label": "R.A. 9851, Sec. 6 – Other Crimes against Humanity", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2009/ra_9851_2009.html",
             "specific_sections": "Sec. 6"},
            {"statute_id": "RA-8344", "provision_id": "general",
             "label": "B.P. 702 as amended by R.A. 8344 – Refusal of Emergency Treatment", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra1997/ra_8344_1997.html"},
        ]
    },

    # C — Public Order
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "C", "sub_heading": "Title Three – Crimes against Public Order",
        "sort_order": 13,
        "provisions": [
            {"statute_id": "RA-10591", "provision_id": "3,28-41",
             "label": "R.A. 10591, Secs. 3 & 28-41 – Comprehensive Firearms and Ammunition Regulation Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2013/ra_10591_2013.html",
             "specific_sections": "Secs. 3, 28-41"},
            {"statute_id": "PD-1829", "provision_id": "general",
             "label": "P.D. 1829 – Obstruction of Justice", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1981/pd_1829_1981.html"},
            {"statute_id": "PD-532", "provision_id": "general",
             "label": "P.D. 532 – Highway Robbery / Brigandage", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1974/pd_532_1974.html"},
        ]
    },

    # D — Public Interest / Cybercrime
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "D", "sub_heading": "Title Four – Crimes against Public Interest (Cybercrime)",
        "sort_order": 14,
        "provisions": [
            {"statute_id": "RA-10175", "provision_id": "4b1-4b3,4a6",
             "label": "R.A. 10175 – Cybercrime Prevention Act: Computer-related Forgery, Fraud, Identity Theft, Cybersquatting", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2012/ra_10175_2012.html",
             "specific_sections": "Secs. 4(a)(6), 4(b)(1), 4(b)(2), 4(b)(3)"},
        ]
    },

    # E — Dangerous Drugs
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "E", "sub_heading": "Dangerous Drugs Crimes",
        "sort_order": 15,
        "provisions": [
            {"statute_id": "RA-9165", "provision_id": "general",
             "label": "R.A. 9165 – Comprehensive Dangerous Drugs Act, as amended by R.A. 10640", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2002/ra_9165_2002.html",
             "specific_sections": "Secs. 5, 11, 12, 13, 14, 15, 16, 21, 25, 81, 98"},
        ]
    },

    # F — Public Morals
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "F", "sub_heading": "Title Six – Crimes against Public Morals",
        "sort_order": 16,
        "provisions": [
            {"statute_id": "PD-1602", "provision_id": "general",
             "label": "P.D. 1602 as amended by R.A. 9287 – Anti-Gambling Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2004/ra_9287_2004.html"},
            {"statute_id": "RPC", "provision_id": "133", "label": "Art. 133 – Offending religious feelings", "source": "db"},
            {"statute_id": "RPC", "provision_id": "201", "label": "Art. 201 – Immoral doctrines, obscene publications", "source": "db"},
        ]
    },

    # G — Public Officers (Plunder, Graft)
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "G", "sub_heading": "Title Seven – Crimes Committed by Public Officers",
        "sort_order": 17,
        "provisions": [
            {"statute_id": "RA-7080", "provision_id": "general",
             "label": "R.A. 7080 – Plunder Act, as amended", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra1991/ra_7080_1991.html"},
            {"statute_id": "RA-3019", "provision_id": "general",
             "label": "R.A. 3019 – Anti-Graft and Corrupt Practices Act, as amended", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra1960/ra_3019_1960.html"},
            {"statute_id": "RA-6713", "provision_id": "general",
             "label": "R.A. 6713 – Code of Conduct and Ethical Standards for Public Officials", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra1989/ra_6713_1989.html"},
            {"statute_id": "RA-11596", "provision_id": "general",
             "label": "R.A. 11596 – Prohibition of Child Marriage (Facilitation by Public Officers)", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2021/ra_11596_2021.html"},
        ]
    },

    # H — Crimes Against Persons
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "H", "sub_heading": "Title Eight – Crimes against Persons",
        "sort_order": 18,
        "provisions": [
            {"statute_id": "RA-9208", "provision_id": "general",
             "label": "R.A. 9208 – Anti-Trafficking in Persons Act, as amended by R.A. 10364", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2003/ra_9208_2003.html"},
            {"statute_id": "RA-9262", "provision_id": "general",
             "label": "R.A. 9262 – Anti-Violence Against Women and their Children (VAWC) Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2004/ra_9262_2004.html"},
            {"statute_id": "RA-7610", "provision_id": "5-9,12",
             "label": "R.A. 7610 – Special Protection of Children Against Abuse (Secs. 5-9, 12)", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra1992/ra_7610_1992.html",
             "specific_sections": "Secs. 5, 6, 7, 8, 9, 12"},
            {"statute_id": "RA-11930", "provision_id": "general",
             "label": "R.A. 11930 – Anti-Online Sexual Abuse or Exploitation of Children (OSAEC) Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2022/ra_11930_2022.html"},
            {"statute_id": "RA-11648", "provision_id": "general",
             "label": "R.A. 11648 – Providing Stronger Protection Against Rape, Sexual Exploitation and Sexual Abuse", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2022/ra_11648_2022.html"},
            {"statute_id": "RA-11313", "provision_id": "3-7,11-12,14",
             "label": "R.A. 11313, Secs. 3-7, 11-12, 14 – Safe Spaces Act (Sexual Harassment)", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2019/ra_11313_2019.html",
             "specific_sections": "Secs. 3-7, 11-12, 14"},
            {"statute_id": "RA-11053", "provision_id": "general",
             "label": "R.A. 8049 as amended by R.A. 11053 – Anti-Hazing Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2018/ra_11053_2018.html"},
        ]
    },

    # I — Personal Liberty / Cybercrime
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "I", "sub_heading": "Title Nine – Crimes against Personal Liberty and Security (Cybercrime)",
        "sort_order": 19,
        "provisions": [
            {"statute_id": "RA-10175", "provision_id": "4a1-4a5",
             "label": "R.A. 10175, Sec. 4(a)(1)-(5) – Offenses against Confidentiality, Integrity, Availability", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2012/ra_10175_2012.html",
             "specific_sections": "Secs. 4(a)(1)-(5)"},
            {"statute_id": "RA-8792", "provision_id": "33a",
             "label": "R.A. 8792, Sec. 33(a) – E-Commerce Act; Hacking/Cracking", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2000/ra_8792_2000.html",
             "specific_sections": "Sec. 33(a)"},
        ]
    },

    # J — Property
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "J", "sub_heading": "Title Ten – Crimes against Property",
        "sort_order": 20,
        "provisions": [
            {"statute_id": "PD-1612", "provision_id": "general",
             "label": "P.D. 1612 – Anti-Fencing Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1979/pd_1612_1979.html"},
            {"statute_id": "PD-533", "provision_id": "general",
             "label": "P.D. 533 – Anti-Cattle Rustling Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1974/pd_533_1974.html"},
            {"statute_id": "PD-1613", "provision_id": "general",
             "label": "P.D. 1613 – Arson Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1979/pd_1613_1979.html"},
            {"statute_id": "RA-10883", "provision_id": "general",
             "label": "R.A. 10883 as amended by R.A. 11235 – Anti-Carnapping Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2016/ra_10883_2016.html"},
            {"statute_id": "BP-22", "provision_id": "general",
             "label": "B.P. 22 – Bouncing Checks Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/bpblg/bp_22_1979.html"},
            {"statute_id": "PD-1689", "provision_id": "general",
             "label": "P.D. 1689 – Swindling by Syndicate", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/presdecs/pd1980/pd_1689_1980.html"},
            {"statute_id": "RA-8792", "provision_id": "33b",
             "label": "R.A. 8792, Sec. 33(b) – E-Commerce Act; Intellectual Property Piracy", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2000/ra_8792_2000.html",
             "specific_sections": "Sec. 33(b)"},
        ]
    },

    # K — Chastity
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "K", "sub_heading": "Title Eleven – Crimes against Chastity",
        "sort_order": 21,
        "provisions": [
            {"statute_id": "RA-9995", "provision_id": "general",
             "label": "R.A. 9995 – Anti-Photo and Video Voyeurism Act", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2009/ra_9995_2009.html"},
            {"statute_id": "RA-7610", "provision_id": "5b",
             "label": "R.A. 7610, Sec. 5(b) – Lascivious Conduct against Children", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra1992/ra_7610_1992.html",
             "specific_sections": "Sec. 5(b)"},
        ]
    },

    # L — Civil Status
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "L", "sub_heading": "Title Twelve – Crimes against the Civil Status of Persons",
        "sort_order": 22,
        "provisions": [
            {"statute_id": "CA-148", "provision_id": "general",
             "label": "C.A. 148 as amended by R.A. 6805 – Anti-Alias Law", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/statutes/comacts/ca_148_1936.html"},
            {"statute_id": "RPC", "provision_id": "177", "label": "Art. 177 – Usurpation of authority or official functions", "source": "db"},
            {"statute_id": "RPC", "provision_id": "178", "label": "Art. 178 – Using fictitious name and concealing true name", "source": "db"},
            {"statute_id": "RPC", "provision_id": "348", "label": "Art. 348 – Simulation of births; substitution of one child for another", "source": "db"},
        ]
    },

    # M — Honor
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "M", "sub_heading": "Title Thirteen – Crimes against Honor (Cyber Libel)",
        "sort_order": 23,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "353", "label": "Art. 353 – Definition of libel", "source": "db"},
            {"statute_id": "RPC", "provision_id": "354", "label": "Art. 354 – Requirement of publicity", "source": "db"},
            {"statute_id": "RPC", "provision_id": "355", "label": "Art. 355 – Libel by means of writing", "source": "db"},
            {"statute_id": "RA-10175", "provision_id": "4c4",
             "label": "R.A. 10175, Sec. 4(c)(4) – Cyber Libel", "source": "scrape",
             "scrape_url": f"{LAWPHIL}/repacts/ra2012/ra_10175_2012.html",
             "specific_sections": "Sec. 4(c)(4)"},
        ]
    },

    # N — Quasi-offenses
    {
        "roman_num": "III", "topic_heading": "Crimes and Their Penalties",
        "sub_letter": "N", "sub_heading": "Title Fourteen – Quasi-offenses (Criminal Negligence)",
        "sort_order": 24,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "365", "label": "Art. 365 – Imprudence and negligence (quasi-offenses)", "source": "db"},
            # Syllabus specifically cites this case as the governing doctrine
            {
                "statute_id": "CASE", "provision_id": "GR-240337",
                "label": "Morales v. People, G.R. No. 240337 (Jan. 2, 2022) – Quasi-offenses doctrine",
                "source": "db_case",   # pulled from sc_decided_cases, not codal
            },
        ]
    },
]

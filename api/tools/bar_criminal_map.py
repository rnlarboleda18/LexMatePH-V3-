"""
Criminal Law — 2026 Bar Syllabus Topic-to-Provision Map
"""

CRIMINAL_MAP = [
    # ── I. FUNDAMENTAL PRINCIPLES ─────────────────────────────────────────────
    {
        "roman_num": "I",
        "topic_heading": "FUNDAMENTAL PRINCIPLES",
        "sub_letter": "A",
        "sub_heading": "Construction or Interpretation of Penal Laws",
        "detail": (
            "A. Construction or Interpretation of Penal Laws\n"
            "   1. Effects of Repeal or Amendment\n"
            "   2. Retroactive Effect of Penal Laws\n"
            "   3. Pro Reo Principle or Rule of Lenity\n"
            "   4. Suppletory Application of Revised Penal Code to Special Laws – RPC, Art. 10"
        ),
        "sort_order": 1,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "1", "label": "Art. 1 – Time when Act takes effect", "source": "db"},
            {"statute_id": "RPC", "provision_id": "2", "label": "Art. 2 – Application of penal laws", "source": "db"},
            {"statute_id": "RPC", "provision_id": "10", "label": "Art. 10 – Offenses not subject to RPC; suppletory application", "source": "db"},
            {"statute_id": "RPC", "provision_id": "22", "label": "Art. 22 – Retroactive effect of penal laws", "source": "db"},
        ]
    },
    {
        "roman_num": "I",
        "topic_heading": "FUNDAMENTAL PRINCIPLES",
        "sub_letter": "B",
        "sub_heading": "Nullum Crimen, Nulla Poena Sine Lege",
        "detail": "B. Nullum Crimen, Nulla Poena Sine Lege",
        "sort_order": 2,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "1", "label": "Art. 1 – No crime without law", "source": "db"},
            {"statute_id": "RPC", "provision_id": "21", "label": "Art. 21 – No felony without a law penalizing it", "source": "db"},
        ]
    },
    {
        "roman_num": "I",
        "topic_heading": "FUNDAMENTAL PRINCIPLES",
        "sub_letter": "C",
        "sub_heading": "Mala In Se and Mala Prohibita",
        "detail": "C. Mala In Se and Mala Prohibita",
        "sort_order": 3,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "3", "label": "Art. 3 – Felonies (dolo vs culpa)", "source": "db"},
            {"statute_id": "RPC", "provision_id": "10", "label": "Art. 10 – Suppletory application to special laws", "source": "db"},
        ]
    },
    {
        "roman_num": "I",
        "topic_heading": "FUNDAMENTAL PRINCIPLES",
        "sub_letter": "D",
        "sub_heading": "Cardinal Principles of Criminal Law",
        "detail": (
            "D. Cardinal Principles of Criminal Law\n"
            "   1. Generality\n"
            "   2. Territoriality\n"
            "   3. Prospectivity"
        ),
        "sort_order": 4,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "2", "label": "Art. 2 – Territoriality and exceptions", "source": "db"},
            {"statute_id": "RPC", "provision_id": "22", "label": "Art. 22 – Prospectivity; retroactive effect when favorable", "source": "db"},
        ]
    },
    {
        "roman_num": "I",
        "topic_heading": "FUNDAMENTAL PRINCIPLES",
        "sub_letter": "E",
        "sub_heading": "Constitutional Limitations on the Power to Enact Penal Laws",
        "detail": (
            "E. Constitutional Limitations on the Power to Enact Penal Laws\n"
            "   1. Equal Protection\n"
            "   2. Due Process\n"
            "   3. Bill of Attainder\n"
            "   4. Ex Post Facto Law\n"
            "   5. Excessive Fines, Cruel, Degrading, or Inhuman Punishment"
        ),
        "sort_order": 5,
        "provisions": [
            {"statute_id": "CONST", "provision_id": "III-1", "label": "Art. III, Sec. 1 – Due Process and Equal Protection", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-19", "label": "Art. III, Sec. 19 – Prohibition on excessive fines and cruel punishment", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-22", "label": "Art. III, Sec. 22 – Ex post facto laws and bills of attainder", "source": "db"},
        ]
    },

    # ── II. FELONIES AND CRIMINAL LIABILITY ───────────────────────────────────
    {
        "roman_num": "II",
        "topic_heading": "FELONIES AND CRIMINAL LIABILITY",
        "sub_letter": "A",
        "sub_heading": "Felonies",
        "detail": (
            "A. Felonies\n"
            "   1. Definition\n"
            "   2. Dolo and Culpa\n"
            "   3. Felony and Crime, Distinguished\n"
            "   4. Gravity\n"
            "   5. Stages of Execution\n"
            "      a. Subjective Phase and Objective Phase\n"
            "      b. Spontaneous Desistance\n"
            "      c. Attempted, Frustrated, and Consummated Stages\n"
            "      d. Preparatory and Overt Acts\n"
            "   6. Plurality of Crimes\n"
            "      a. Absorption Principle\n"
            "      b. Single Impulse Rule\n"
            "      c. Compound Complex Crime\n"
            "      d. Complex Crime Proper\n"
            "      e. Special Complex Crime or Composite Crimes\n"
            "      f. Continuous or Continuing Crime"
        ),
        "sort_order": 6,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "3", "label": "Art. 3 – Felonies defined; dolo and culpa", "source": "db"},
            {"statute_id": "RPC", "provision_id": "4", "label": "Art. 4 – Criminal liability; proximate cause", "source": "db"},
            {"statute_id": "RPC", "provision_id": "6", "label": "Art. 6 – Stages of execution (consummated, frustrated, attempted)", "source": "db"},
            {"statute_id": "RPC", "provision_id": "7", "label": "Art. 7 – When light felonies are punishable", "source": "db"},
            {"statute_id": "RPC", "provision_id": "48", "label": "Art. 48 – Complex crimes (compound and complex proper)", "source": "db"},
        ]
    },
    {
        "roman_num": "II",
        "topic_heading": "FELONIES AND CRIMINAL LIABILITY",
        "sub_letter": "B",
        "sub_heading": "Criminal Liability",
        "detail": (
            "B. Criminal Liability\n"
            "   1. Actus Reus and Mens Rea\n"
            "   2. Criminal Causation\n"
            "      a. Proximate Cause\n"
            "      b. Efficient Intervening Cause\n"
            "   3. Aberratio Ictus, Error In Personae, and Praeter Intentionem\n"
            "   4. Impossible Crime\n"
            "   5. Duty of Courts when Act is Non-punishable or Penalty is Excessive\n"
            "   6. Participation in Acts Giving Rise to Criminal Liability\n"
            "      a. Principals, Accomplices, and Accessories\n"
            "         i. Fencers – P.D. No. 1612\n"
            "         ii. Obstructors of Criminal Prosecution – P.D. No. 1829\n"
            "      b. Conspiracy and Proposal\n"
            "         i. As a Mode of Incurring Criminal Liability\n"
            "         ii. As a Criminal Act\n"
            "   7. Circumstances Affecting Criminal Liability\n"
            "      a. Justifying Circumstances – RPC, Art. 11\n"
            "      b. Exempting Circumstances – RPC, Art. 12\n"
            "         i. Minority – R.A. No. 9344, Sec. 6, as amended\n"
            "         ii. Battered Woman Syndrome – R.A. No. 9262\n"
            "      c. Mitigating Circumstances – RPC, Art. 13\n"
            "      d. Aggravating Circumstances – RPC, Art. 14\n"
            "         i. Using Loose Firearm – R.A. No. 10591, Sec. 29\n"
            "         ii. Being under the Influence of Dangerous Drugs – R.A. No. 9165, Sec. 25\n"
            "         iii. Using Information and Communications Technologies – R.A. No. 10175, Sec. 6\n"
            "      e. Alternative Circumstances – RPC, Art. 15\n"
            "      f. Absolutory Causes\n"
            "      g. Instigation and Entrapment\n"
            "   8. Effect of Repeat Commission of Crimes\n"
            "      a. Recidivism – RPC Art. 14(9)\n"
            "      b. Quasi-recidivism – RPC Art. 160\n"
            "      c. Habituality – RPC Art. 14(10)\n"
            "      d. Habitual Delinquency – RPC Art. 62(5)\n"
            "   9. Criminal Liability of Minors – R.A. No. 9344, as amended"
        ),
        "sort_order": 7,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "89", "label": "Art. 89 – How criminal liability is totally extinguished", "source": "db"},
            {"statute_id": "RPC", "provision_id": "90", "label": "Art. 90 – Prescription of crimes", "source": "db"},
            {"statute_id": "RPC", "provision_id": "91", "label": "Art. 91 – Computation of prescription of offenses", "source": "db"},
            {"statute_id": "RPC", "provision_id": "92", "label": "Art. 92 – Prescription of penalties", "source": "db"},
            {"statute_id": "RPC", "provision_id": "94", "label": "Art. 94 – Partial extinction of criminal liability", "source": "db"},
            {"statute_id": "ACT-3326", "provision_id": "general", "label": "Act No. 3326 – Prescription of offenses under special laws", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/acts/act_3326.html"},
            {"statute_id": "RA-10592", "provision_id": "general", "label": "R.A. 10592 – GCTA; partial extinction", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2013/ra_10592_2013.html"},
        ]
    },
    {
        "roman_num": "II",
        "topic_heading": "FELONIES AND CRIMINAL LIABILITY",
        "sub_letter": "C",
        "sub_heading": "Penalties",
        "detail": (
            "C. Penalties\n"
            "   1. Classification\n"
            "   2. Principal and Accessory Penalties\n"
            "   3. Duration and Effects\n"
            "   4. Application and Graduation\n"
            "   5. Determination of Imposable Penalty\n"
            "   6. Preventive Imprisonment\n"
            "   7. Subsidiary Penalty\n"
            "   8. Execution and Service\n"
            "      a. Community Service – R.A. No. 11362; A.M. No. 20-06-14-SC\n"
            "      b. Recognizance – R.A. No. 10389\n"
            "      c. Successive Service of Sentence\n"
            "      d. Three-Fold Rule\n"
            "      e. Indeterminate Sentence Law – Act No. 4103, as amended\n"
            "      f. Probation – P.D. No. 968, as amended"
        ),
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
            {"statute_id": "ACT-4103", "provision_id": "general", "label": "Act No. 4103 – Indeterminate Sentence Law", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/acts/act_4103.html"},
            {"statute_id": "PD-968", "provision_id": "general", "label": "P.D. 968 – Probation Law, as amended", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1976/pd_968_1976.html"},
            {"statute_id": "RA-10389", "provision_id": "general", "label": "R.A. 10389 – Recognizance Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2013/ra_10389_2013.html"},
            {"statute_id": "RA-11362", "provision_id": "general", "label": "R.A. 11362 – Community Service Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2019/ra_11362_2019.html"},
            {"statute_id": "RA-10592", "provision_id": "general", "label": "R.A. 10592 – Good Conduct Time Allowance (GCTA)", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2013/ra_10592_2013.html"},
            {"statute_id": "RA-9344", "provision_id": "general", "label": "R.A. 9344 – Juvenile Justice and Welfare Act (criminal liability of minors)", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2006/ra_9344_2006.html", "specific_sections": "Secs. 6, 57-58"},
        ]
    },
    {
        "roman_num": "II",
        "topic_heading": "FELONIES AND CRIMINAL LIABILITY",
        "sub_letter": "D",
        "sub_heading": "Extinction of Criminal Liability",
        "detail": (
            "D. Extinction of Criminal Liability\n"
            "   1. Total Extinction\n"
            "      a. Death of Convict\n"
            "      b. Service of Sentence\n"
            "      c. Amnesty\n"
            "      d. Absolute Pardon\n"
            "      e. Prescription\n"
            "         i. Prescription of Crimes\n"
            "         ii. Act No. 3326\n"
            "         iii. Prescription of Penalties\n"
            "      f. Marriage between the Offender and the Offended Party\n"
            "   2. Partial Extinction\n"
            "      a. Conditional Pardon – Act No. 1524\n"
            "      b. Commutation of Sentence\n"
            "      c. Good Conduct Time Allowance – R.A. No. 10592\n"
            "      d. Parole"
        ),
        "sort_order": 9,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "89", "label": "Art. 89 – How criminal liability is totally extinguished", "source": "db"},
            {"statute_id": "RPC", "provision_id": "90", "label": "Art. 90 – Prescription of crimes", "source": "db"},
            {"statute_id": "RPC", "provision_id": "91", "label": "Art. 91 – Computation of prescription of offenses", "source": "db"},
            {"statute_id": "RPC", "provision_id": "92", "label": "Art. 92 – Prescription of penalties", "source": "db"},
            {"statute_id": "RPC", "provision_id": "94", "label": "Art. 94 – Partial extinction of criminal liability", "source": "db"},
            {"statute_id": "ACT-3326", "provision_id": "general", "label": "Act No. 3326 – Prescription of offenses under special laws", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/acts/act_3326.html"},
            {"statute_id": "RA-10592", "provision_id": "general", "label": "R.A. 10592 – GCTA; partial extinction", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2013/ra_10592_2013.html"},
        ]
    },
    {
        "roman_num": "II",
        "topic_heading": "FELONIES AND CRIMINAL LIABILITY",
        "sub_letter": "E",
        "sub_heading": "Civil Liability Ex Delicto",
        "detail": (
            "E. Civil Liability Ex Delicto\n"
            "   1. Primary and Subsidiary\n"
            "   2. Restitution, Reparation, and Indemnification\n"
            "   3. Civil Liability of an Offender Exempted from Criminal Liability\n"
            "   4. Share of Each Person Civilly Liable for a Felony\n"
            "   5. Preference in Payment\n"
            "   6. Extinction and Survival of Civil Liability Ex Delicto"
        ),
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

    # ── III. CRIMES AND THEIR PENALTIES ──────────────────────────────────────
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "A",
        "sub_heading": "Title One – Crimes against National Security and the Law of Nations",
        "detail": (
            "A. Title One – Crimes against National Security and the Law of Nations\n"
            "   1. Piracy – P.D. No. 532\n"
            "   2. Terrorism – R.A. No. 11479\n"
            "   3. Terrorism Financing – R.A. No. 10168\n"
            "   4. Genocide and War Crimes – R.A. No. 9851, Secs. 4 and 5"
        ),
        "sort_order": 11,
        "provisions": [
            {"statute_id": "PD-532", "provision_id": "general", "label": "P.D. 532 – Anti-Piracy and Anti-Highway Robbery Law", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1974/pd_532_1974.html"},
            {"statute_id": "RA-11479", "provision_id": "general", "label": "R.A. 11479 – Anti-Terrorism Act of 2020", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2020/ra_11479_2020.html"},
            {"statute_id": "RA-10168", "provision_id": "general", "label": "R.A. 10168 – Terrorism Financing Prevention and Suppression Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2012/ra_10168_2012.html"},
            {"statute_id": "RA-9851", "provision_id": "4-5", "label": "R.A. 9851, Secs. 4 & 5 – Philippine Act on Crimes Against International Humanitarian Law (Genocide, War Crimes)", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2009/ra_9851_2009.html", "specific_sections": "Secs. 4, 5"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "B",
        "sub_heading": "Title Two – Crimes against the Fundamental Laws of the State",
        "detail": (
            "B. Title Two – Crimes against the Fundamental Laws of the State\n"
            "   1. Torture – R.A. No. 9745\n"
            "   2. Other Crimes against Humanity – R.A. No. 9851, Sec. 6\n"
            "   3. Refusal of Emergency Treatment – Batas Pambansa [B.P.] Blg. 702, as amended by R.A. No. 8344"
        ),
        "sort_order": 12,
        "provisions": [
            {"statute_id": "RA-9745", "provision_id": "general", "label": "R.A. 9745 – Anti-Torture Act of 2009", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2009/ra_9745_2009.html"},
            {"statute_id": "RA-9851", "provision_id": "6", "label": "R.A. 9851, Sec. 6 – Other Crimes against Humanity", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2009/ra_9851_2009.html", "specific_sections": "Sec. 6"},
            {"statute_id": "RA-8344", "provision_id": "general", "label": "B.P. 702 as amended by R.A. 8344 – Refusal of Emergency Treatment", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra1997/ra_8344_1997.html"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "C",
        "sub_heading": "Title Three – Crimes against Public Order",
        "detail": (
            "C. Title Three – Crimes against Public Order\n"
            "   1. Crimes relating to Firearms and Ammunition – R.A. No. 10591, Secs. 3 and 28-41\n"
            "   2. Obstruction of Justice – P.D. No. 1829\n"
            "   3. Highway Robbery – P.D. No. 532"
        ),
        "sort_order": 13,
        "provisions": [
            {"statute_id": "RA-10591", "provision_id": "3,28-41", "label": "R.A. 10591, Secs. 3 & 28-41 – Comprehensive Firearms and Ammunition Regulation Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2013/ra_10591_2013.html", "specific_sections": "Secs. 3, 28-41"},
            {"statute_id": "PD-1829", "provision_id": "general", "label": "P.D. 1829 – Obstruction of Justice", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1981/pd_1829_1981.html"},
            {"statute_id": "PD-532", "provision_id": "general", "label": "P.D. 532 – Highway Robbery / Brigandage", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1974/pd_532_1974.html"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "D",
        "sub_heading": "Title Four – Crimes against Public Interest",
        "detail": (
            "D. Title Four – Crimes against Public Interest\n"
            "   1. Computer-related Forgery – R.A. No. 10175, Sec. 4(b)(1)\n"
            "   2. Computer-related Fraud – R.A. No. 10175, Sec. 4(b)(2)\n"
            "   3. Computer-related Identity Theft – R.A. No. 10175, Sec. 4(b)(3)\n"
            "   4. Cyber-squatting – R.A. No. 10175, Sec. 4(a)(6)"
        ),
        "sort_order": 14,
        "provisions": [
            {"statute_id": "RA-10175", "provision_id": "4b1-4b3,4a6", "label": "R.A. 10175 – Cybercrime Prevention Act: Computer-related Forgery, Fraud, Identity Theft, Cybersquatting", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2012/ra_10175_2012.html", "specific_sections": "Secs. 4(a)(6), 4(b)(1), 4(b)(2), 4(b)(3)"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "E",
        "sub_heading": "Dangerous Drugs Crimes – R.A. No. 9165, as amended by R.A. No. 10640",
        "detail": (
            "E. Dangerous Drugs Crimes – R.A. No. 9165, as amended by R.A. No. 10640 and its IRR; A.M. No. 18-03-16-SC"
        ),
        "sort_order": 15,
        "provisions": [
            {"statute_id": "RA-9165", "provision_id": "general", "label": "R.A. 9165 – Comprehensive Dangerous Drugs Act, as amended by R.A. 10640", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2002/ra_9165_2002.html", "specific_sections": "Secs. 5, 11, 12, 13, 14, 15, 16, 21, 25, 81, 98"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "F",
        "sub_heading": "Title Six – Crimes against Public Morals",
        "detail": (
            "F. Title Six – Crimes against Public Morals\n"
            "   1. Gambling – P.D. No. 1602, as amended by R.A. No. 9287\n"
            "   2. Immoral Doctrines – RPC, Arts. 133 and 201"
        ),
        "sort_order": 16,
        "provisions": [
            {"statute_id": "PD-1602", "provision_id": "general", "label": "P.D. 1602 as amended by R.A. 9287 – Anti-Gambling Law", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2004/ra_9287_2004.html"},
            {"statute_id": "RPC", "provision_id": "133", "label": "Art. 133 – Offending religious feelings", "source": "db"},
            {"statute_id": "RPC", "provision_id": "201", "label": "Art. 201 – Immoral doctrines, obscene publications", "source": "db"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "G",
        "sub_heading": "Title Seven – Crimes Committed by Public Officers",
        "detail": (
            "G. Title Seven – Crimes Committed by Public Officers\n"
            "   1. Plunder – R.A. No. 7080, as amended\n"
            "      a. Definitions\n"
            "      b. Series and Combination\n"
            "      c. Pattern\n"
            "      d. Wheel and Chain Conspiracy\n"
            "   2. Graft and Corrupt Practices – R.A. No. 3019, as amended\n"
            "   3. Unethical Conduct – R.A. No. 6713\n"
            "   4. Facilitation of Child Marriage – R.A. No. 11596"
        ),
        "sort_order": 17,
        "provisions": [
            {"statute_id": "RA-7080", "provision_id": "general", "label": "R.A. 7080 – Plunder Act, as amended", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra1991/ra_7080_1991.html"},
            {"statute_id": "RA-3019", "provision_id": "general", "label": "R.A. 3019 – Anti-Graft and Corrupt Practices Act, as amended", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra1960/ra_3019_1960.html"},
            {"statute_id": "RA-6713", "provision_id": "general", "label": "R.A. 6713 – Code of Conduct and Ethical Standards for Public Officials", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra1989/ra_6713_1989.html"},
            {"statute_id": "RA-11596", "provision_id": "general", "label": "R.A. 11596 – Prohibition of Child Marriage (Facilitation by Public Officers)", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2021/ra_11596_2021.html"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "H",
        "sub_heading": "Title Eight – Crimes against Persons",
        "detail": (
            "H. Title Eight – Crimes against Persons\n"
            "   1. Human Trafficking – R.A. No. 9208, as amended\n"
            "   2. Violence Against Women and their Children (VAWC) – R.A. No. 9262\n"
            "   3. Abuse of Children – R.A. No. 7610, as amended\n"
            "      a. Attempt to Commit Child Prostitution – Sec. 6\n"
            "      b. Child Prostitution and Other Sexual Abuse – Sec. 5\n"
            "      c. Attempt to Commit Child Trafficking – Sec. 8\n"
            "      d. Child Trafficking – Sec. 7\n"
            "      e. Obscene Publication and Indecent Shows – Sec. 9\n"
            "      f. Child Labor – Sec. 12\n"
            "      g. Child Pornography – R.A. No. 11930, in relation to R.A. No. 10175, Sec. 4(c)(2)\n"
            "      h. Child Marriage – R.A. No. 11596\n"
            "   4. Rape, Sexual Exploitation, and Sexual Abuse – R.A. No. 11648\n"
            "   5. Sexual Harassment – R.A. No. 11313, Secs. 3-7, 11-12, and 14\n"
            "   6. Hazing – R.A. No. 8049, as amended by R.A. No. 11053"
        ),
        "sort_order": 18,
        "provisions": [
            {"statute_id": "RA-9208", "provision_id": "general", "label": "R.A. 9208 – Anti-Trafficking in Persons Act, as amended by R.A. 10364", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2003/ra_9208_2003.html"},
            {"statute_id": "RA-9262", "provision_id": "general", "label": "R.A. 9262 – Anti-Violence Against Women and their Children (VAWC) Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2004/ra_9262_2004.html"},
            {"statute_id": "RA-7610", "provision_id": "5-9,12", "label": "R.A. 7610 – Special Protection of Children Against Abuse (Secs. 5-9, 12)", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra1992/ra_7610_1992.html", "specific_sections": "Secs. 5, 6, 7, 8, 9, 12"},
            {"statute_id": "RA-11930", "provision_id": "general", "label": "R.A. 11930 – Anti-Online Sexual Abuse or Exploitation of Children (OSAEC) Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2022/ra_11930_2022.html"},
            {"statute_id": "RA-11648", "provision_id": "general", "label": "R.A. 11648 – Providing Stronger Protection Against Rape, Sexual Exploitation and Sexual Abuse", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2022/ra_11648_2022.html"},
            {"statute_id": "RA-11313", "provision_id": "3-7,11-12,14", "label": "R.A. 11313, Secs. 3-7, 11-12, 14 – Safe Spaces Act (Sexual Harassment)", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2019/ra_11313_2019.html", "specific_sections": "Secs. 3-7, 11-12, 14"},
            {"statute_id": "RA-11053", "provision_id": "general", "label": "R.A. 8049 as amended by R.A. 11053 – Anti-Hazing Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2018/ra_11053_2018.html"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "I",
        "sub_heading": "Title Nine – Crimes against Personal Liberty and Security",
        "detail": (
            "I. Title Nine – Crimes against Personal Liberty and Security\n"
            "   1. Offenses against Confidentiality, Integrity, and Availability of Computer Data and Systems\n"
            "      – R.A. No. 10175, Sec. 4(a)(1) to (5)\n"
            "   2. Hacking/Cracking – R.A. No. 8792, Sec. 33(a)"
        ),
        "sort_order": 19,
        "provisions": [
            {"statute_id": "RA-10175", "provision_id": "4a1-4a5", "label": "R.A. 10175, Sec. 4(a)(1)-(5) – Offenses against Confidentiality, Integrity, Availability", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2012/ra_10175_2012.html", "specific_sections": "Secs. 4(a)(1)-(5)"},
            {"statute_id": "RA-8792", "provision_id": "33a", "label": "R.A. 8792, Sec. 33(a) – E-Commerce Act; Hacking/Cracking", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2000/ra_8792_2000.html", "specific_sections": "Sec. 33(a)"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "J",
        "sub_heading": "Title Ten – Crimes against Property",
        "detail": (
            "J. Title Ten – Crimes against Property\n"
            "   1. Fencing – P.D. No. 1612\n"
            "   2. Cattle Rustling – P.D. No. 533\n"
            "   3. Arson – P.D. No. 1613\n"
            "   4. Carnapping – R.A. No. 10883; R.A. No. 11235\n"
            "   5. Issuance of Bouncing Checks – B.P. Blg. 22; Administrative Circular [A.C.] No. 12-2000; A.C. No. 13-2001\n"
            "   6. Swindling by Syndicate – P.D. No. 1689\n"
            "   7. Intellectual Property Piracy – R.A. No. 8792, Sec. 33(b)"
        ),
        "sort_order": 20,
        "provisions": [
            {"statute_id": "PD-1612", "provision_id": "general", "label": "P.D. 1612 – Anti-Fencing Law", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1979/pd_1612_1979.html"},
            {"statute_id": "PD-533", "provision_id": "general", "label": "P.D. 533 – Anti-Cattle Rustling Law", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1974/pd_533_1974.html"},
            {"statute_id": "PD-1613", "provision_id": "general", "label": "P.D. 1613 – Arson Law", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1979/pd_1613_1979.html"},
            {"statute_id": "RA-10883", "provision_id": "general", "label": "R.A. 10883 as amended by R.A. 11235 – Anti-Carnapping Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2016/ra_10883_2016.html"},
            {"statute_id": "BP-22", "provision_id": "general", "label": "B.P. 22 – Bouncing Checks Law", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/bpblg/bp_22_1979.html"},
            {"statute_id": "PD-1689", "provision_id": "general", "label": "P.D. 1689 – Swindling by Syndicate", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/presdecs/pd1980/pd_1689_1980.html"},
            {"statute_id": "RA-8792", "provision_id": "33b", "label": "R.A. 8792, Sec. 33(b) – E-Commerce Act; Intellectual Property Piracy", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2000/ra_8792_2000.html", "specific_sections": "Sec. 33(b)"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "K",
        "sub_heading": "Title Eleven – Crimes against Chastity",
        "detail": (
            "K. Title Eleven – Crimes against Chastity\n"
            "   1. Photo and Video Voyeurism – R.A. No. 9995\n"
            "   2. Lascivious Conduct – R.A. No. 7610, Sec. 5(b)"
        ),
        "sort_order": 21,
        "provisions": [
            {"statute_id": "RA-9995", "provision_id": "general", "label": "R.A. 9995 – Anti-Photo and Video Voyeurism Act", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2009/ra_9995_2009.html"},
            {"statute_id": "RA-7610", "provision_id": "5b", "label": "R.A. 7610, Sec. 5(b) – Lascivious Conduct against Children", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra1992/ra_7610_1992.html", "specific_sections": "Sec. 5(b)"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "L",
        "sub_heading": "Title Twelve – Crimes against the Civil Status of Persons",
        "detail": (
            "L. Title Twelve – Crimes against the Civil Status of Persons\n"
            "   1. Unauthorized Use of Alias – Commonwealth Act No. 148, as amended by R.A. No. 6805;\n"
            "      RPC, Arts. 177-178 and 348"
        ),
        "sort_order": 22,
        "provisions": [
            {"statute_id": "CA-148", "provision_id": "general", "label": "C.A. 148 as amended by R.A. 6805 – Anti-Alias Law", "source": "scrape", "scrape_url": "https://lawphil.net/statutes/comacts/ca_148_1936.html"},
            {"statute_id": "RPC", "provision_id": "177", "label": "Art. 177 – Usurpation of authority or official functions", "source": "db"},
            {"statute_id": "RPC", "provision_id": "178", "label": "Art. 178 – Using fictitious name and concealing true name", "source": "db"},
            {"statute_id": "RPC", "provision_id": "348", "label": "Art. 348 – Simulation of births; substitution of one child for another", "source": "db"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "M",
        "sub_heading": "Title Thirteen – Crimes against Honor",
        "detail": (
            "M. Title Thirteen – Crimes against Honor\n"
            "   1. Cyber Libel – R.A. No. 10175, Sec. 4(c)(4)"
        ),
        "sort_order": 23,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "353", "label": "Art. 353 – Definition of libel", "source": "db"},
            {"statute_id": "RPC", "provision_id": "354", "label": "Art. 354 – Requirement of publicity", "source": "db"},
            {"statute_id": "RPC", "provision_id": "355", "label": "Art. 355 – Libel by means of writing", "source": "db"},
            {"statute_id": "RA-10175", "provision_id": "4c4", "label": "R.A. 10175, Sec. 4(c)(4) – Cyber Libel", "source": "scrape", "scrape_url": "https://lawphil.net/repacts/ra2012/ra_10175_2012.html", "specific_sections": "Sec. 4(c)(4)"},
        ]
    },
    {
        "roman_num": "III",
        "topic_heading": "CRIMES AND THEIR PENALTIES",
        "sub_letter": "N",
        "sub_heading": "Title Fourteen – Quasi-offenses – Morales v. People, G.R. No. 240337, January 2, 2022",
        "detail": (
            "N. Title Fourteen – Quasi-offenses – Morales v. People, G.R. No. 240337, January 2, 2022"
        ),
        "sort_order": 24,
        "provisions": [
            {"statute_id": "RPC", "provision_id": "365", "label": "Art. 365 – Imprudence and negligence (quasi-offenses)", "source": "db"},
            {"statute_id": "CASE", "provision_id": "GR-240337", "label": "Morales v. People, G.R. No. 240337 (Jan. 2, 2022) – Quasi-offenses doctrine", "source": "db_case"},
        ]
    },
]

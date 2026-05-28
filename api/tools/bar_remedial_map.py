"""
Remedial Law, Legal and Judicial Ethics — 2026 Bar Syllabus Topic-to-Provision Map
Case cutoff: June 30, 2025
Weight: 25% (highest)

Roman numerals I–XII correspond EXACTLY to the 12 official syllabus topics:
  I.    Jurisdiction
  II.   Civil Procedure (A.M. No. 19-10-20-SC)
  III.  Post-judgment Remedies
  IV.   Execution of Judgments
  V.    Provisional Remedies
  VI.   Special Civil Actions
  VII.  Special Proceedings
  VIII. Criminal Procedure
  IX.   Evidence
  X.    Legal and Judicial Ethics — CPRA (incl. Notarial Practice)
  XI.   Judicial Ethics
  XII.  Practical Exercises

source='db'     → provision is in the app's DB (roc_codal, sc_issuances_codal, etc.)
source='scrape' → provision scraped from LawPhil or SC eLib
source='ai'     → no codal text; AI synthesizes from SC rules and case law
"""

LAWPHIL = "https://lawphil.net"
ELIB    = "https://elibrary.judiciary.gov.ph"

REMEDIAL_MAP = [

    # ──────────────────────────────────────────────────────────────────────────
    # I. JURISDICTION
    # Syllabus: Subject Matter, Acquired, Philippine Courts — MTC, RTC, CA, SC,
    #           Sandiganbayan, CTA, Family Courts, RA 11576, Lupong Tagapamayapa
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "I", "topic_heading": "Jurisdiction",
        "sub_letter": "A",
        "sub_heading": "Concept, Types, and Acquisition; MTC, RTC, CA, SC (RA 7691 as amended by RA 11576)",
        "sort_order": 1,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "1-3",  "label": "Rule 1, Sec. 3 – Cases governed", "source": "db"},
            {
                "statute_id": "RA-7691", "provision_id": "general",
                "label": "R.A. 7691 – Expanding MTC Jurisdiction (as amended by R.A. 11576)",
                "source": "scrape",
                "scrape_url": f"{LAWPHIL}/statutes/repacts/ra1994/ra_7691_1994.html",
            },
            {
                "statute_id": "RA-11576", "provision_id": "general",
                "label": "R.A. 11576 – Expanded Jurisdiction Act (2021)",
                "source": "scrape",
                "scrape_url": f"{ELIB}/republic_acts/11576",
            },
            {
                "statute_id": "BP-129", "provision_id": "general",
                "label": "B.P. 129 – Judiciary Reorganization Act (RTC, CA jurisdiction)",
                "source": "scrape",
                "scrape_url": f"{LAWPHIL}/statutes/bpblg/bp_129_1980.html",
            },
        ]
    },
    {
        "roman_num": "I", "topic_heading": "Jurisdiction",
        "sub_letter": "B",
        "sub_heading": "Sandiganbayan (RA 8249), Court of Tax Appeals (RA 9282), and Family Courts (RA 8369)",
        "sort_order": 2,
        "provisions": [
            {
                "statute_id": "RA-8249", "provision_id": "general",
                "label": "R.A. 8249 – Sandiganbayan Jurisdiction",
                "source": "scrape",
                "scrape_url": f"{LAWPHIL}/statutes/repacts/ra1997/ra_8249_1997.html",
            },
            {
                "statute_id": "RA-9282", "provision_id": "general",
                "label": "R.A. 9282 – Court of Tax Appeals (expanded jurisdiction)",
                "source": "scrape",
                "scrape_url": f"{LAWPHIL}/statutes/repacts/ra2004/ra_9282_2004.html",
            },
            {
                "statute_id": "RA-8369", "provision_id": "general",
                "label": "R.A. 8369 – Family Courts Act",
                "source": "scrape",
                "scrape_url": f"{LAWPHIL}/statutes/repacts/ra1997/ra_8369_1997.html",
            },
        ]
    },
    {
        "roman_num": "I", "topic_heading": "Jurisdiction",
        "sub_letter": "C",
        "sub_heading": "Katarungang Pambarangay — Lupong Tagapamayapa (R.A. 7160)",
        "sort_order": 3,
        "provisions": [
            # RA 7160 (Local Government Code), Book III, Title I — Katarungang Pambarangay
            # Sections 399-422. Text hardcoded because the law is too large for AI synthesis
            # to return structured JSON reliably. Source: sc.judiciary.gov.ph / lawphil.net.
            {
                "statute_id": "LGC", "provision_id": "399",
                "label": "R.A. 7160, Sec. 399 – Lupong Tagapamayapa",
                "source": "inline",
                "text": (
                    "**Sec. 399. Lupong Tagapamayapa.**\n\n"
                    "There is hereby created in each barangay a lupong tagapamayapa, "
                    "hereinafter referred to as the lupon, composed of the punong barangay "
                    "as chairman and ten (10) to twenty (20) members. The lupon shall be "
                    "constituted every three (3) years in the manner provided herein.\n\n"
                    "Any person actually residing or working in the barangay, not otherwise "
                    "expressly disqualified by law, and possessing integrity, impartiality, "
                    "independence of mind, sense of fairness, and reputation for probity, "
                    "may be appointed a member of the lupon.\n\n"
                    "A member of the lupon may be removed for cause by the punong barangay "
                    "with the concurrence of a majority of all the lupon members. The punong "
                    "barangay may also remove a member upon petition of at least one-fourth "
                    "(1/4) of all barangay residents of legal age."
                ),
            },
            {
                "statute_id": "LGC", "provision_id": "408",
                "label": "R.A. 7160, Sec. 408 – Subject Matter for Amicable Settlement; Exceptions",
                "source": "inline",
                "text": (
                    "**Sec. 408. Subject Matter for Amicable Settlement; Exceptions Thereto.**\n\n"
                    "The lupon of each barangay shall have authority to bring together the parties "
                    "actually residing in the same city or municipality for amicable settlement of "
                    "all disputes except:\n\n"
                    "(a) Where one party is the government, or any subdivision or instrumentality thereof;\n"
                    "(b) Where one party is a public officer or employee, and the dispute relates "
                    "to the performance of his official functions;\n"
                    "(c) Offenses punishable by imprisonment exceeding one (1) year or a fine "
                    "exceeding Five thousand pesos (P5,000.00);\n"
                    "(d) Offenses where there is no private offended party;\n"
                    "(e) Where the dispute involves real properties located in different cities or "
                    "municipalities unless the parties thereto agree to submit their differences "
                    "to amicable settlement by an appropriate lupon;\n"
                    "(f) Disputes involving parties who actually reside in barangays of different "
                    "cities or municipalities, except where such barangay units adjoin each other "
                    "and the parties thereto agree to submit their differences to amicable "
                    "settlement by an appropriate lupon; and\n"
                    "(g) Such other classes of disputes which the President may determine in the "
                    "interest of justice or upon the recommendation of the Secretary of Justice.\n\n"
                    "The court in which non-criminal cases not falling within the authority of the "
                    "lupon under this Code are filed may, at any time before trial, motu proprio "
                    "refer the case to the lupon concerned for amicable settlement."
                ),
            },
            {
                "statute_id": "LGC", "provision_id": "409",
                "label": "R.A. 7160, Sec. 409 – Venue",
                "source": "inline",
                "text": (
                    "**Sec. 409. Venue.**\n\n"
                    "(a) Disputes between persons actually residing in the same barangay shall be "
                    "brought for amicable settlement before the lupon of said barangay.\n\n"
                    "(b) Those involving actual residents of different barangays within the same "
                    "city or municipality shall be brought in the barangay where the respondent "
                    "or any of the respondents actually resides, at the election of the complainant.\n\n"
                    "(c) All disputes involving real property or any interest therein shall be "
                    "brought in the barangay where the real property or the larger portion "
                    "thereof is situated.\n\n"
                    "(d) Those arising at the workplace where the contending parties are employed "
                    "or at the institution where such parties are enrolled for study, shall be "
                    "brought in the barangay where such workplace or institution is located."
                ),
            },
            {
                "statute_id": "LGC", "provision_id": "412",
                "label": "R.A. 7160, Sec. 412 – Conciliation; Pre-condition to Filing in Court",
                "source": "inline",
                "text": (
                    "**Sec. 412. Conciliation.**\n\n"
                    "(a) *Pre-condition to Filing of Complaint in Court.* — No complaint, petition, "
                    "action, or proceeding involving any matter within the authority of the lupon "
                    "shall be filed or instituted directly in court or any other government office "
                    "for adjudication, unless there has been a confrontation between the parties "
                    "before the lupon chairman or the pangkat, and that no conciliation or "
                    "settlement has been reached as certified by the lupon secretary or pangkat "
                    "secretary as attested to by the lupon or pangkat chairman or unless the "
                    "settlement has been repudiated by the parties thereto.\n\n"
                    "(b) *Where Parties May Go Directly to Court.* — The parties may go directly "
                    "to court in the following instances:\n"
                    "(1) Where the accused is under detention;\n"
                    "(2) Where a person has otherwise been deprived of personal liberty calling "
                    "for habeas corpus proceedings;\n"
                    "(3) Where actions are coupled with provisional remedies such as preliminary "
                    "injunction, attachment, delivery of personal property, and support "
                    "pendente lite; and\n"
                    "(4) Where the action may otherwise be barred by the statute of limitations.\n\n"
                    "(c) *Conciliation among members of indigenous cultural communities.* — The "
                    "customs and traditions of indigenous cultural communities shall be applied "
                    "in settling disputes between members of the cultural communities."
                ),
            },
            {
                "statute_id": "LGC", "provision_id": "416",
                "label": "R.A. 7160, Sec. 416 – Effect of Amicable Settlement and Arbitration Award",
                "source": "inline",
                "text": (
                    "**Sec. 416. Effect of Amicable Settlement and Arbitration Award.**\n\n"
                    "The amicable settlement and arbitration award shall have the force and effect "
                    "of a final judgment of a court upon the expiration of ten (10) days from the "
                    "date thereof, unless repudiation of the settlement has been made or a petition "
                    "to nullify the award has been filed before the proper city or municipal court. "
                    "However, this provision shall not apply to court cases settled by the lupon "
                    "under the last paragraph of Section 408 of this Code, in which case the "
                    "compromise settlement agreed upon by the parties before the lupon chairman or "
                    "the pangkat shall be submitted to the court and upon approval thereof, have "
                    "the force and effect of a judgment of said court."
                ),
            },
            {
                "statute_id": "LGC", "provision_id": "417",
                "label": "R.A. 7160, Sec. 417 – Execution",
                "source": "inline",
                "text": (
                    "**Sec. 417. Execution.**\n\n"
                    "The amicable settlement or arbitration award may be enforced by execution by "
                    "the lupon within six (6) months from the date of the settlement. After the "
                    "lapse of such time, the settlement may be enforced by action in the "
                    "appropriate city or municipal court."
                ),
            },
            {
                "statute_id": "LGC", "provision_id": "418",
                "label": "R.A. 7160, Sec. 418 – Repudiation",
                "source": "inline",
                "text": (
                    "**Sec. 418. Repudiation.**\n\n"
                    "Any party to the dispute may, within ten (10) days from the date of the "
                    "settlement, repudiate the same by filing with the lupon chairman a statement "
                    "to that effect sworn to before him, where the consent is vitiated by fraud, "
                    "violence, or intimidation. Such repudiation shall be sufficient basis for the "
                    "issuance of the certification for filing a complaint in court or any "
                    "government office for adjudication."
                ),
            },
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # II. CIVIL PROCEDURE (A.M. No. 19-10-20-SC)
    # Syllabus: Classification of Actions, Pleadings, Summons, Motions,
    #           Dismissal, Default, Pre-trial, Modes of Discovery, Trial, Judgments
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "II", "topic_heading": "Civil Procedure (A.M. No. 19-10-20-SC)",
        "sub_letter": "A",
        "sub_heading": "Classification of Actions; Cause of Action; Splitting; Joinder; Venue (Rules 1-2, 4)",
        "sort_order": 4,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "1-1",  "label": "Rule 1, Sec. 1 – Title of the Rules", "source": "db"},
            {"statute_id": "ROC", "provision_id": "1-2",  "label": "Rule 1, Sec. 2 – In what courts applicable", "source": "db"},
            {"statute_id": "ROC", "provision_id": "1-6",  "label": "Rule 1, Sec. 6 – Construction", "source": "db"},
            {"statute_id": "ROC", "provision_id": "2-1",  "label": "Rule 2, Sec. 1 – Ordinary civil actions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "2-2",  "label": "Rule 2, Sec. 2 – Cause of action defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "2-4",  "label": "Rule 2, Sec. 4 – Splitting a single cause of action", "source": "db"},
            {"statute_id": "ROC", "provision_id": "2-5",  "label": "Rule 2, Sec. 5 – Joinder of causes of action", "source": "db"},
            {"statute_id": "ROC", "provision_id": "4-1",  "label": "Rule 4, Sec. 1 – Venue of real actions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "4-2",  "label": "Rule 4, Sec. 2 – Venue of personal actions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "4-3",  "label": "Rule 4, Sec. 3 – Venue; actions against nonresidents", "source": "db"},
            {"statute_id": "ROC", "provision_id": "4-4",  "label": "Rule 4, Sec. 4 – When Rule not applicable", "source": "db"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Civil Procedure (A.M. No. 19-10-20-SC)",
        "sub_letter": "B",
        "sub_heading": "Parties; Pleadings; Forum Shopping (Rules 3, 6-11)",
        "sort_order": 5,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "3-1",  "label": "Rule 3, Sec. 1 – Who may be parties", "source": "db"},
            {"statute_id": "ROC", "provision_id": "3-2",  "label": "Rule 3, Sec. 2 – Parties in interest", "source": "db"},
            {"statute_id": "ROC", "provision_id": "3-7",  "label": "Rule 3, Sec. 7 – Compulsory joinder of indispensable parties", "source": "db"},
            {"statute_id": "ROC", "provision_id": "3-8",  "label": "Rule 3, Sec. 8 – Necessary party", "source": "db"},
            {"statute_id": "ROC", "provision_id": "6-1",  "label": "Rule 6, Sec. 1 – Pleadings defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "6-3",  "label": "Rule 6, Sec. 3 – Complaint", "source": "db"},
            {"statute_id": "ROC", "provision_id": "6-4",  "label": "Rule 6, Sec. 4 – Answer", "source": "db"},
            {"statute_id": "ROC", "provision_id": "6-6",  "label": "Rule 6, Sec. 6 – Counterclaim", "source": "db"},
            {"statute_id": "ROC", "provision_id": "6-7",  "label": "Rule 6, Sec. 7 – Compulsory counterclaim", "source": "db"},
            {"statute_id": "ROC", "provision_id": "6-8",  "label": "Rule 6, Sec. 8 – Cross-claim", "source": "db"},
            {"statute_id": "ROC", "provision_id": "7-4",  "label": "Rule 7, Sec. 4 – Verification", "source": "db"},
            {"statute_id": "ROC", "provision_id": "7-5",  "label": "Rule 7, Sec. 5 – Certification against forum shopping", "source": "db"},
            {"statute_id": "ROC", "provision_id": "8-1",  "label": "Rule 8, Sec. 1 – Manner of making allegations", "source": "db"},
            {"statute_id": "ROC", "provision_id": "10-2", "label": "Rule 10, Sec. 2 – Amendments as a matter of right", "source": "db"},
            {"statute_id": "ROC", "provision_id": "10-3", "label": "Rule 10, Sec. 3 – Amendments by leave of court", "source": "db"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Civil Procedure (A.M. No. 19-10-20-SC)",
        "sub_letter": "C",
        "sub_heading": "Summons (Rule 14); Filing and Service (Rule 13); Motions; Dismissal; Default (Rules 9, 15, 17)",
        "sort_order": 6,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "14-1",  "label": "Rule 14, Sec. 1 – Clerk to issue summons", "source": "db"},
            {"statute_id": "ROC", "provision_id": "14-6",  "label": "Rule 14, Sec. 6 – Service in person on defendant", "source": "db"},
            {"statute_id": "ROC", "provision_id": "14-7",  "label": "Rule 14, Sec. 7 – Substituted service", "source": "db"},
            {"statute_id": "ROC", "provision_id": "14-12", "label": "Rule 14, Sec. 12 – Service upon foreign private juridical entity", "source": "db"},
            {"statute_id": "ROC", "provision_id": "14-16", "label": "Rule 14, Sec. 16 – Service by publication", "source": "db"},
            {"statute_id": "ROC", "provision_id": "13-5",  "label": "Rule 13, Sec. 5 – Modes of service", "source": "db"},
            {"statute_id": "ROC", "provision_id": "13-9",  "label": "Rule 13, Sec. 9 – Service by electronic means", "source": "db"},
            {"statute_id": "ROC", "provision_id": "9-1",   "label": "Rule 9, Sec. 1 – Defenses and objections not pleaded; waiver", "source": "db"},
            {"statute_id": "ROC", "provision_id": "9-3",   "label": "Rule 9, Sec. 3 – Default; declaration of", "source": "db"},
            {"statute_id": "ROC", "provision_id": "15-4",  "label": "Rule 15, Sec. 4 – Non-litigious motions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "15-5",  "label": "Rule 15, Sec. 5 – Litigious motions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "17-1",  "label": "Rule 17, Sec. 1 – Dismissal upon notice by plaintiff", "source": "db"},
            {"statute_id": "ROC", "provision_id": "17-3",  "label": "Rule 17, Sec. 3 – Dismissal due to fault of plaintiff", "source": "db"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Civil Procedure (A.M. No. 19-10-20-SC)",
        "sub_letter": "D",
        "sub_heading": "Pre-trial; Judicial Dispute Resolution (Rule 18)",
        "sort_order": 7,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "18-1",  "label": "Rule 18, Sec. 1 – When conducted", "source": "db"},
            {"statute_id": "ROC", "provision_id": "18-2",  "label": "Rule 18, Sec. 2 – Pre-trial conference", "source": "db"},
            {"statute_id": "ROC", "provision_id": "18-6",  "label": "Rule 18, Sec. 6 – Pre-trial order", "source": "db"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Civil Procedure (A.M. No. 19-10-20-SC)",
        "sub_letter": "E",
        "sub_heading": "Modes of Discovery (Rules 23-29)",
        "sort_order": 8,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "23-1",  "label": "Rule 23, Sec. 1 – Depositions pending action", "source": "db"},
            {"statute_id": "ROC", "provision_id": "23-4",  "label": "Rule 23, Sec. 4 – Use of depositions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "25-1",  "label": "Rule 25, Sec. 1 – Interrogatories to parties", "source": "db"},
            {"statute_id": "ROC", "provision_id": "26-1",  "label": "Rule 26, Sec. 1 – Request for admission", "source": "db"},
            {"statute_id": "ROC", "provision_id": "27-1",  "label": "Rule 27, Sec. 1 – Production or inspection of documents", "source": "db"},
            {"statute_id": "ROC", "provision_id": "28-1",  "label": "Rule 28, Sec. 1 – Physical and mental examination of persons", "source": "db"},
            {"statute_id": "ROC", "provision_id": "29-1",  "label": "Rule 29, Sec. 1 – Refusal to answer; consequences", "source": "db"},
        ]
    },
    {
        "roman_num": "II", "topic_heading": "Civil Procedure (A.M. No. 19-10-20-SC)",
        "sub_letter": "F",
        "sub_heading": "Trial; Summary Judgment; Judgment on Pleadings; Judgments (Rules 30, 34-36)",
        "sort_order": 9,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "30-1",  "label": "Rule 30, Sec. 1 – Notice of trial", "source": "db"},
            {"statute_id": "ROC", "provision_id": "35-1",  "label": "Rule 35, Sec. 1 – Summary judgment for claimant", "source": "db"},
            {"statute_id": "ROC", "provision_id": "35-2",  "label": "Rule 35, Sec. 2 – Summary judgment for defending party", "source": "db"},
            {"statute_id": "ROC", "provision_id": "36-1",  "label": "Rule 36, Sec. 1 – Rendition of judgments and final orders", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # III. POST-JUDGMENT REMEDIES
    # Syllabus: New Trial, Reconsideration, Relief from Judgment Rule 38,
    #           Annulment of Judgment Rule 47, Appeal Rules 40-45 and 64
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "III", "topic_heading": "Post-judgment Remedies",
        "sub_letter": "A",
        "sub_heading": "New Trial and Reconsideration (Rule 37)",
        "sort_order": 10,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "37-1",  "label": "Rule 37, Sec. 1 – Grounds for new trial or reconsideration", "source": "db"},
            {"statute_id": "ROC", "provision_id": "37-2",  "label": "Rule 37, Sec. 2 – Contents of motion for new trial", "source": "db"},
        ]
    },
    {
        "roman_num": "III", "topic_heading": "Post-judgment Remedies",
        "sub_letter": "B",
        "sub_heading": "Relief from Judgment (Rule 38) and Annulment of Judgment (Rule 47)",
        "sort_order": 11,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "38-1",  "label": "Rule 38, Sec. 1 – Petition for relief from judgment", "source": "db"},
            {"statute_id": "ROC", "provision_id": "38-3",  "label": "Rule 38, Sec. 3 – Time for filing petition", "source": "db"},
            {"statute_id": "ROC", "provision_id": "47-1",  "label": "Rule 47, Sec. 1 – Coverage of annulment of judgment", "source": "db"},
            {"statute_id": "ROC", "provision_id": "47-2",  "label": "Rule 47, Sec. 2 – Grounds for annulment", "source": "db"},
            {"statute_id": "ROC", "provision_id": "47-3",  "label": "Rule 47, Sec. 3 – Period for filing action", "source": "db"},
        ]
    },
    {
        "roman_num": "III", "topic_heading": "Post-judgment Remedies",
        "sub_letter": "C",
        "sub_heading": "Appeals — Rules 40-45 and Rule 64; Modes of Appeal; Certiorari Distinguished",
        "sort_order": 12,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "40-1",  "label": "Rule 40, Sec. 1 – Appeal from MTC to RTC", "source": "db"},
            {"statute_id": "ROC", "provision_id": "41-1",  "label": "Rule 41, Sec. 1 – Appeal from RTC; modes", "source": "db"},
            {"statute_id": "ROC", "provision_id": "42-1",  "label": "Rule 42 – Petition for review from RTC to CA", "source": "db"},
            {"statute_id": "ROC", "provision_id": "43-1",  "label": "Rule 43 – Appeal from quasi-judicial agencies to CA", "source": "db"},
            {"statute_id": "ROC", "provision_id": "45-1",  "label": "Rule 45 – Petition for review on certiorari (SC)", "source": "db"},
            {"statute_id": "ROC", "provision_id": "64-1",  "label": "Rule 64, Sec. 1 – Scope — review of COMELEC/COA decisions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "64-2",  "label": "Rule 64, Sec. 2 – Mode of review (via Rule 65 certiorari)", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # IV. EXECUTION OF JUDGMENTS
    # Syllabus: Rule 39, Res Judicata, Enforcement of Foreign Judgments
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "IV", "topic_heading": "Execution of Judgments",
        "sub_letter": "A",
        "sub_heading": "Execution upon Judgments; Satisfaction; Writ of Execution (Rule 39)",
        "sort_order": 13,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "39-1",  "label": "Rule 39, Sec. 1 – Execution upon judgments or final orders", "source": "db"},
            {"statute_id": "ROC", "provision_id": "39-6",  "label": "Rule 39, Sec. 6 – Execution by motion or independent action", "source": "db"},
        ]
    },
    {
        "roman_num": "IV", "topic_heading": "Execution of Judgments",
        "sub_letter": "B",
        "sub_heading": "Res Judicata; Enforcement of Foreign Judgments (Rule 39, Secs. 47-48)",
        "sort_order": 14,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "39-47", "label": "Rule 39, Sec. 47 – Effect of judgments (res judicata)", "source": "db"},
            {"statute_id": "ROC", "provision_id": "39-48", "label": "Rule 39, Sec. 48 – Effect of foreign judgments or final orders", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # V. PROVISIONAL REMEDIES
    # Syllabus: Attachment Rule 57, Preliminary Injunction Rule 58,
    #           Receivership, Replevin, Support Pendente Lite
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "V", "topic_heading": "Provisional Remedies",
        "sub_letter": "A",
        "sub_heading": "Preliminary Attachment (Rule 57)",
        "sort_order": 15,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "57-1",  "label": "Rule 57, Sec. 1 – Grounds for preliminary attachment", "source": "db"},
            {"statute_id": "ROC", "provision_id": "57-5",  "label": "Rule 57, Sec. 5 – Manner of attaching property", "source": "db"},
            {"statute_id": "ROC", "provision_id": "57-13", "label": "Rule 57, Sec. 13 – Discharge of attachment", "source": "db"},
        ]
    },
    {
        "roman_num": "V", "topic_heading": "Provisional Remedies",
        "sub_letter": "B",
        "sub_heading": "Preliminary Injunction and Temporary Restraining Order (Rule 58)",
        "sort_order": 16,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "58-1",  "label": "Rule 58, Sec. 1 – Preliminary injunction defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "58-3",  "label": "Rule 58, Sec. 3 – Grounds for issuance", "source": "db"},
            {"statute_id": "ROC", "provision_id": "58-5",  "label": "Rule 58, Sec. 5 – Injunction not granted without hearing", "source": "db"},
        ]
    },
    {
        "roman_num": "V", "topic_heading": "Provisional Remedies",
        "sub_letter": "C",
        "sub_heading": "Receivership (Rule 59) and Replevin (Rule 60)",
        "sort_order": 17,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "59-1",  "label": "Rule 59, Sec. 1 – Appointment of receiver", "source": "db"},
            {"statute_id": "ROC", "provision_id": "60-1",  "label": "Rule 60, Sec. 1 – Replevin; when may be issued", "source": "db"},
        ]
    },
    {
        "roman_num": "V", "topic_heading": "Provisional Remedies",
        "sub_letter": "D",
        "sub_heading": "Support Pendente Lite (Rule 61)",
        "sort_order": 18,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "61-1",  "label": "Rule 61, Sec. 1 – Application for support pendente lite", "source": "db"},
            {"statute_id": "ROC", "provision_id": "61-2",  "label": "Rule 61, Sec. 2 – Comment", "source": "db"},
            {"statute_id": "ROC", "provision_id": "61-5",  "label": "Rule 61, Sec. 5 – Enforcement of order", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # VI. SPECIAL CIVIL ACTIONS
    # Syllabus: Interpleader, Declaratory Relief, Certiorari/Prohibition/Mandamus
    #           Rule 65, Quo Warranto, Expropriation, Foreclosure, Partition,
    #           Forcible Entry/Unlawful Detainer Rule 70, Contempt
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "VI", "topic_heading": "Special Civil Actions",
        "sub_letter": "A",
        "sub_heading": "Interpleader (Rule 62) and Declaratory Relief (Rule 63)",
        "sort_order": 19,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "62-1",  "label": "Rule 62, Sec. 1 – When interpleader proper", "source": "db"},
            {"statute_id": "ROC", "provision_id": "63-1",  "label": "Rule 63, Sec. 1 – Who may file petition for declaratory relief", "source": "db"},
            {"statute_id": "ROC", "provision_id": "63-2",  "label": "Rule 63, Sec. 2 – Parties in declaratory relief", "source": "db"},
        ]
    },
    {
        "roman_num": "VI", "topic_heading": "Special Civil Actions",
        "sub_letter": "B",
        "sub_heading": "Certiorari, Prohibition, and Mandamus (Rule 65)",
        "sort_order": 20,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "65-1",  "label": "Rule 65, Sec. 1 – Petition for certiorari", "source": "db"},
            {"statute_id": "ROC", "provision_id": "65-2",  "label": "Rule 65, Sec. 2 – Petition for prohibition", "source": "db"},
            {"statute_id": "ROC", "provision_id": "65-3",  "label": "Rule 65, Sec. 3 – Petition for mandamus", "source": "db"},
            {"statute_id": "ROC", "provision_id": "65-4",  "label": "Rule 65, Sec. 4 – When and where to file petition", "source": "db"},
            {"statute_id": "ROC", "provision_id": "65-8",  "label": "Rule 65, Sec. 8 – Proceedings after comment is filed", "source": "db"},
        ]
    },
    {
        "roman_num": "VI", "topic_heading": "Special Civil Actions",
        "sub_letter": "C",
        "sub_heading": "Quo Warranto (Rule 66)",
        "sort_order": 21,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "66-1",  "label": "Rule 66, Sec. 1 – Action by government", "source": "db"},
            {"statute_id": "ROC", "provision_id": "66-5",  "label": "Rule 66, Sec. 5 – When individual may commence action", "source": "db"},
        ]
    },
    {
        "roman_num": "VI", "topic_heading": "Special Civil Actions",
        "sub_letter": "D",
        "sub_heading": "Expropriation (Rule 67); Foreclosure of Real Estate Mortgage (Rule 68); Partition (Rule 69)",
        "sort_order": 22,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "67-1",  "label": "Rule 67, Sec. 1 – Complaint for expropriation", "source": "db"},
            {"statute_id": "ROC", "provision_id": "67-4",  "label": "Rule 67, Sec. 4 – Order of expropriation", "source": "db"},
            {"statute_id": "ROC", "provision_id": "68-1",  "label": "Rule 68, Sec. 1 – Complaint for foreclosure of mortgage", "source": "db"},
            {"statute_id": "ROC", "provision_id": "68-3",  "label": "Rule 68, Sec. 3 – Sale of mortgaged property", "source": "db"},
            {"statute_id": "ROC", "provision_id": "69-1",  "label": "Rule 69, Sec. 1 – Complaint for partition; order thereon", "source": "db"},
        ]
    },
    {
        "roman_num": "VI", "topic_heading": "Special Civil Actions",
        "sub_letter": "E",
        "sub_heading": "Forcible Entry and Unlawful Detainer (Rule 70); Contempt (Rule 71)",
        "sort_order": 23,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "70-1",  "label": "Rule 70, Sec. 1 – Forcible entry and unlawful detainer", "source": "db"},
            {"statute_id": "ROC", "provision_id": "71-1",  "label": "Rule 71, Sec. 1 – Direct contempt of court", "source": "db"},
            {"statute_id": "ROC", "provision_id": "71-3",  "label": "Rule 71, Sec. 3 – Indirect contempt", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # VII. SPECIAL PROCEEDINGS
    # Syllabus: Settlement of Estate (Extrajudicial Rule 74 / Intestate Rules 78-79 /
    #           Testate Rules 76-77); Guardianship; Habeas Corpus; Amparo; Habeas Data;
    #           Environmental Cases: Kalikasan, TEPO
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "VII", "topic_heading": "Special Proceedings",
        "sub_letter": "A",
        "sub_heading": "Settlement of Estate — Extrajudicial (Rule 74), Intestate (Rules 78-79), Testate (Rules 76-77)",
        "sort_order": 24,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "73-1",  "label": "Rule 73, Sec. 1 – Venue for settlement of estate", "source": "db"},
            {"statute_id": "ROC", "provision_id": "74-1",  "label": "Rule 74, Sec. 1 – Extrajudicial settlement by agreement", "source": "db"},
            {"statute_id": "ROC", "provision_id": "74-2",  "label": "Rule 74, Sec. 2 – Two or more heirs; summary settlement", "source": "db"},
            {"statute_id": "ROC", "provision_id": "79-1",  "label": "Rule 79, Sec. 1 – Opposition to issuance of letters testamentary", "source": "db"},
            {"statute_id": "ROC", "provision_id": "90-1",  "label": "Rule 90, Sec. 1 – Distribution and partition of estate", "source": "db"},
        ]
    },
    {
        "roman_num": "VII", "topic_heading": "Special Proceedings",
        "sub_letter": "B",
        "sub_heading": "Guardianship (Rule 93) and Adoption (R.A. 11642)",
        "sort_order": 25,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "93-1",  "label": "Rule 93, Sec. 1 – Venue for guardianship proceedings", "source": "db"},
            {
                "statute_id": "RA-11642", "provision_id": "general",
                "label": "R.A. 11642 – Domestic Administrative Adoption and Alternative Child Care Act",
                "source": "db",
            },
        ]
    },
    {
        "roman_num": "VII", "topic_heading": "Special Proceedings",
        "sub_letter": "C",
        "sub_heading": "Writ of Habeas Corpus (Rule 102)",
        "sort_order": 26,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "102-1",  "label": "Rule 102, Sec. 1 – To what habeas corpus extends", "source": "db"},
            {"statute_id": "ROC", "provision_id": "102-4",  "label": "Rule 102, Sec. 4 – When writ not allowed or discharged", "source": "db"},
        ]
    },
    {
        "roman_num": "VII", "topic_heading": "Special Proceedings",
        "sub_letter": "D",
        "sub_heading": "Writ of Amparo (A.M. No. 07-9-12-SC) and Writ of Habeas Data (A.M. No. 08-1-16-SC)",
        "sort_order": 27,
        "provisions": [
            {
                "statute_id": "AM-07-9-12-SC", "provision_id": "general",
                "label": "A.M. No. 07-9-12-SC – Rule on the Writ of Amparo",
                "source": "db",
            },
            {
                "statute_id": "AM-08-1-16-SC", "provision_id": "general",
                "label": "A.M. No. 08-1-16-SC – Rule on the Writ of Habeas Data",
                "source": "db",
            },
        ]
    },
    {
        "roman_num": "VII", "topic_heading": "Special Proceedings",
        "sub_letter": "E",
        "sub_heading": "Environmental Cases — Writ of Kalikasan and TEPO (A.M. No. 09-6-8-SC)",
        "sort_order": 28,
        "provisions": [
            {
                "statute_id": "AM-09-6-8-SC", "provision_id": "general",
                "label": "A.M. No. 09-6-8-SC – Rules of Procedure for Environmental Cases (Kalikasan, TEPO)",
                "source": "db",
            },
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # VIII. CRIMINAL PROCEDURE
    # Syllabus: Prosecution of Offenses Rule 110, Civil Action Rule 111,
    #           Preliminary Investigation Rule 112, Arrest Rule 113, Bail Rule 114,
    #           Arraignment Rule 116, Motion to Quash Rule 117, Trial Rule 119,
    #           Search and Seizure Rule 126, A.M. No. 17-11-03-SC Cybercrime Warrants
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "VIII", "topic_heading": "Criminal Procedure",
        "sub_letter": "A",
        "sub_heading": "Prosecution of Offenses (Rule 110) and Civil Action (Rule 111)",
        "sort_order": 29,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "110-1",  "label": "Rule 110, Sec. 1 – Institution of criminal actions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "110-2",  "label": "Rule 110, Sec. 2 – Control of prosecution", "source": "db"},
            {"statute_id": "ROC", "provision_id": "110-3",  "label": "Rule 110, Sec. 3 – Complaint defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "110-4",  "label": "Rule 110, Sec. 4 – Information defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "111-1",  "label": "Rule 111, Sec. 1 – Institution of criminal and civil actions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "111-2",  "label": "Rule 111, Sec. 2 – When separate civil action is suspended", "source": "db"},
            {"statute_id": "ROC", "provision_id": "111-3",  "label": "Rule 111, Sec. 3 – When civil action may proceed independently", "source": "db"},
        ]
    },
    {
        "roman_num": "VIII", "topic_heading": "Criminal Procedure",
        "sub_letter": "B",
        "sub_heading": "Preliminary Investigation (Rule 112)",
        "sort_order": 30,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "112-1",  "label": "Rule 112, Sec. 1 – Preliminary investigation defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "112-2",  "label": "Rule 112, Sec. 2 – Officers authorized to conduct", "source": "db"},
            {"statute_id": "ROC", "provision_id": "112-3",  "label": "Rule 112, Sec. 3 – Procedure", "source": "db"},
            {"statute_id": "ROC", "provision_id": "112-6",  "label": "Rule 112, Sec. 6 – When warrant of arrest may issue", "source": "db"},
        ]
    },
    {
        "roman_num": "VIII", "topic_heading": "Criminal Procedure",
        "sub_letter": "C",
        "sub_heading": "Arrest (Rule 113) and Bail (Rule 114)",
        "sort_order": 31,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "113-1",  "label": "Rule 113, Sec. 1 – Arrest; how made", "source": "db"},
            {"statute_id": "ROC", "provision_id": "113-5",  "label": "Rule 113, Sec. 5 – Arrest without warrant; when lawful", "source": "db"},
            {"statute_id": "ROC", "provision_id": "114-1",  "label": "Rule 114, Sec. 1 – Bail defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "114-5",  "label": "Rule 114, Sec. 5 – Bail discretionary", "source": "db"},
            {"statute_id": "ROC", "provision_id": "114-8",  "label": "Rule 114, Sec. 8 – Capital offense or offense punishable by reclusion perpetua — no bail", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-13", "label": "Art. III, Sec. 13 – Right to bail", "source": "db"},
            {
                "statute_id": "AM-21-06-08", "provision_id": "general",
                "label": "A.M. No. 21-06-08 – Rules on Body-Worn Cameras in Execution of Warrants",
                "source": "ai",
            },
        ]
    },
    {
        "roman_num": "VIII", "topic_heading": "Criminal Procedure",
        "sub_letter": "D",
        "sub_heading": "Arraignment and Plea (Rule 116); Motion to Quash (Rule 117)",
        "sort_order": 32,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "116-1",  "label": "Rule 116, Sec. 1 – Arraignment and plea; how made", "source": "db"},
            {"statute_id": "ROC", "provision_id": "117-1",  "label": "Rule 117, Sec. 1 – Time to move to quash", "source": "db"},
            {"statute_id": "ROC", "provision_id": "117-3",  "label": "Rule 117, Sec. 3 – Grounds for motion to quash (incl. double jeopardy)", "source": "db"},
        ]
    },
    {
        "roman_num": "VIII", "topic_heading": "Criminal Procedure",
        "sub_letter": "E",
        "sub_heading": "Trial (Rule 119); Judgment (Rule 120); Double Jeopardy",
        "sort_order": 33,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "117-3",  "label": "Rule 117, Sec. 3 – Grounds for motion to quash (incl. double jeopardy)", "source": "db"},
            {"statute_id": "ROC", "provision_id": "118-1",  "label": "Rule 118, Sec. 1 – Pre-trial; mandatory in criminal cases", "source": "db"},
            {"statute_id": "ROC", "provision_id": "119-17", "label": "Rule 119, Sec. 17 – Discharge of accused to be state witness", "source": "db"},
            {"statute_id": "ROC", "provision_id": "119-23", "label": "Rule 119, Sec. 23 – Demurrer to evidence", "source": "db"},
            {"statute_id": "ROC", "provision_id": "120-1",  "label": "Rule 120, Sec. 1 – Judgment defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "120-4",  "label": "Rule 120, Sec. 4 – Judgment in case of variance", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-21", "label": "Art. III, Sec. 21 – Double jeopardy", "source": "db"},
        ]
    },
    {
        "roman_num": "VIII", "topic_heading": "Criminal Procedure",
        "sub_letter": "F",
        "sub_heading": "Search and Seizure (Rule 126); Exclusionary Rule; Cybercrime Warrants (A.M. No. 17-11-03-SC)",
        "sort_order": 34,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "126-1",  "label": "Rule 126, Sec. 1 – Search warrant defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "126-3",  "label": "Rule 126, Sec. 3 – Requisites for issuing search warrant", "source": "db"},
            {"statute_id": "ROC", "provision_id": "126-5",  "label": "Rule 126, Sec. 5 – Validity of search warrant", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-2",  "label": "Art. III, Sec. 2 – Right against unreasonable searches and seizures", "source": "db"},
            {"statute_id": "CONST", "provision_id": "III-3",  "label": "Art. III, Sec. 3(2) – Exclusionary rule; fruit of the poisonous tree", "source": "db"},
            {
                "statute_id": "AM-17-11-03-SC", "provision_id": "general",
                "label": "A.M. No. 17-11-03-SC – Rule on Cybercrime Warrants",
                "source": "ai",
            },
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # IX. EVIDENCE
    # Syllabus: Admissibility, Judicial Notice, Judicial Admissions, Burden of Proof,
    #           Presumptions, Object Evidence, Documentary Evidence, Testimonial Evidence,
    #           Hearsay Rule, Opinion Rule, Electronic Evidence, DNA Evidence
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "IX", "topic_heading": "Evidence",
        "sub_letter": "A",
        "sub_heading": "Admissibility; Judicial Notice; Judicial Admissions; Burden of Proof; Presumptions (Rules 128-129, 131)",
        "sort_order": 35,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "128-1",  "label": "Rule 128, Sec. 1 – Evidence defined", "source": "db"},
            {"statute_id": "ROC", "provision_id": "128-3",  "label": "Rule 128, Sec. 3 – Admissibility of evidence", "source": "db"},
            {"statute_id": "ROC", "provision_id": "129-1",  "label": "Rule 129, Sec. 1 – Mandatory judicial notice", "source": "db"},
            {"statute_id": "ROC", "provision_id": "129-2",  "label": "Rule 129, Sec. 2 – Discretionary judicial notice", "source": "db"},
            {"statute_id": "ROC", "provision_id": "129-3",  "label": "Rule 129, Sec. 3 – Judicial admissions", "source": "db"},
            {"statute_id": "ROC", "provision_id": "131-1",  "label": "Rule 131, Sec. 1 – Burden of proof; onus probandi", "source": "db"},
            {"statute_id": "ROC", "provision_id": "131-3",  "label": "Rule 131, Sec. 3 – Disputable presumptions", "source": "db"},
        ]
    },
    {
        "roman_num": "IX", "topic_heading": "Evidence",
        "sub_letter": "B",
        "sub_heading": "Object (Real) Evidence; Documentary Evidence; Original Document Rule; Parol Evidence Rule (Rule 130)",
        "sort_order": 36,
        "provisions": [
            # Object Evidence — Rule 130, Sec. 1 under 2019 Revised Rules on Evidence
            {
                "statute_id": "AM-19-08-15-SC", "provision_id": "general",
                "label": "A.M. No. 19-08-15-SC – 2019 Revised Rules on Evidence (Object, Documentary, Original Document Rule)",
                "source": "scrape",
                "scrape_url": f"{LAWPHIL}/courts/supreme/am/am_19_08_15_sc_2019.html",
            },
            {"statute_id": "ROC", "provision_id": "130-1",  "label": "Rule 130, Sec. 1 – Object (real) evidence", "source": "db"},
            {"statute_id": "ROC", "provision_id": "130-3",  "label": "Rule 130, Sec. 3 – Secondary evidence when original is unavailable", "source": "db"},
            {"statute_id": "ROC", "provision_id": "130-9",  "label": "Rule 130, Sec. 9 – Parol evidence rule", "source": "db"},
        ]
    },
    {
        "roman_num": "IX", "topic_heading": "Evidence",
        "sub_letter": "C",
        "sub_heading": "Testimonial Evidence; Privilege; Hearsay Rule; Dying Declaration; Opinion Rule (Rule 130)",
        "sort_order": 37,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "130-25", "label": "Rule 130, Sec. 25 – Parental and filial privilege", "source": "db"},
            {"statute_id": "ROC", "provision_id": "130-37", "label": "Rule 130, Sec. 37 – Hearsay rule", "source": "db"},
            {"statute_id": "ROC", "provision_id": "130-38", "label": "Rule 130, Sec. 38 – Dying declaration", "source": "db"},
            {"statute_id": "ROC", "provision_id": "130-40", "label": "Rule 130, Sec. 40 – Declaration against interest", "source": "db"},
            # Opinion Rule — Rule 130, Secs. 49-50 under 2019 amendments
            {
                "statute_id": "ROC", "provision_id": "130-49",
                "label": "Rule 130, Sec. 49 – Opinion of expert witnesses (Opinion Rule)",
                "source": "db",
            },
            {
                "statute_id": "ROC", "provision_id": "130-50",
                "label": "Rule 130, Sec. 50 – Opinion of ordinary witnesses",
                "source": "db",
            },
        ]
    },
    {
        "roman_num": "IX", "topic_heading": "Evidence",
        "sub_letter": "D",
        "sub_heading": "Electronic Evidence (A.M. No. 01-7-01-SC) and DNA Evidence (A.M. No. 06-11-5-SC)",
        "sort_order": 38,
        "provisions": [
            {
                "statute_id": "AM-01-7-01-SC", "provision_id": "general",
                "label": "A.M. No. 01-7-01-SC – Rules on Electronic Evidence",
                "source": "db",
            },
            {
                "statute_id": "AM-06-11-5-SC", "provision_id": "general",
                "label": "A.M. No. 06-11-5-SC – Revised Rule on DNA Evidence",
                "source": "ai",
            },
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # X. LEGAL AND JUDICIAL ETHICS — CPRA
    # Syllabus: Practice of Law, Admission to Bar, Duties of Lawyers under
    #           Canons I-VI: Independence, Propriety, Fidelity, Competence, Equality;
    #           Discipline and Disbarment; Notarial Practice A.M. No. 02-8-13-SC
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "X", "topic_heading": "Legal and Judicial Ethics — CPRA",
        "sub_letter": "A",
        "sub_heading": "Practice of Law; Admission to Bar (Rule 138); CPRA Overview (A.M. No. 22-09-01-SC)",
        "sort_order": 39,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "138-1",  "label": "Rule 138, Sec. 1 – Who may practice law", "source": "db"},
            {"statute_id": "ROC", "provision_id": "138-5",  "label": "Rule 138, Sec. 5 – Additional requirements for other applicants", "source": "db"},
            {
                "statute_id": "CPRA", "provision_id": "general",
                "label": "Code of Professional Responsibility and Accountability (A.M. No. 22-09-01-SC, 2023) — Full Text",
                "source": "db",
            },
        ]
    },
    {
        "roman_num": "X", "topic_heading": "Legal and Judicial Ethics — CPRA",
        "sub_letter": "B",
        "sub_heading": "CPRA Canons I-III: Independence, Propriety, and Fidelity",
        "sort_order": 40,
        "provisions": [
            {
                "statute_id": "CPRA", "provision_id": "canon1",
                "label": "CPRA – Canon I: Independence",
                "source": "db",
            },
            {
                "statute_id": "CPRA", "provision_id": "canon2",
                "label": "CPRA – Canon II: Propriety",
                "source": "db",
            },
            {
                "statute_id": "CPRA", "provision_id": "canon3",
                "label": "CPRA – Canon III: Fidelity (to Courts, Clients, Profession, and Society)",
                "source": "db",
            },
        ]
    },
    {
        "roman_num": "X", "topic_heading": "Legal and Judicial Ethics — CPRA",
        "sub_letter": "C",
        "sub_heading": "CPRA Canons IV-V: Competence and Equality; Privileged Communication; Conflict of Interest",
        "sort_order": 41,
        "provisions": [
            {
                "statute_id": "CPRA", "provision_id": "canon4",
                "label": "CPRA – Canon IV: Competence and Diligence (incl. confidentiality, conflict of interest)",
                "source": "db",
            },
            {
                "statute_id": "CPRA", "provision_id": "canon5",
                "label": "CPRA – Canon V: Equality",
                "source": "db",
            },
        ]
    },
    {
        "roman_num": "X", "topic_heading": "Legal and Judicial Ethics — CPRA",
        "sub_letter": "D",
        "sub_heading": "Discipline and Disbarment — CPRA Canon VI; IBP Proceedings (Rule 139-B)",
        "sort_order": 42,
        "provisions": [
            {
                "statute_id": "CPRA", "provision_id": "canon6",
                "label": "CPRA – Canon VI: Accountability and Sanctions",
                "source": "db",
            },
            {"statute_id": "ROC", "provision_id": "139-1",  "label": "Rule 139-B, Sec. 1 – Proceedings for disbarment or discipline", "source": "db"},
        ]
    },
    {
        "roman_num": "X", "topic_heading": "Legal and Judicial Ethics — CPRA",
        "sub_letter": "E",
        "sub_heading": "Notarial Practice (A.M. No. 02-8-13-SC)",
        "sort_order": 43,
        "provisions": [
            {
                "statute_id": "AM-02-8-13-SC", "provision_id": "general",
                "label": "A.M. No. 02-8-13-SC – 2004 Rules on Notarial Practice",
                "source": "db",
            },
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # XI. JUDICIAL ETHICS
    # Syllabus: NCJC A.M. No. 03-05-01-SC: Independence, Integrity, Impartiality,
    #           Propriety, Equality, Competence; Discipline of Judges Rule 140
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "XI", "topic_heading": "Judicial Ethics",
        "sub_letter": "A",
        "sub_heading": "New Code of Judicial Conduct (A.M. No. 03-05-01-SC): Independence, Integrity, Impartiality, Propriety, Equality, Competence",
        "sort_order": 44,
        "provisions": [
            {
                "statute_id": "NCJC", "provision_id": "general",
                "label": "New Code of Judicial Conduct for the Philippine Judiciary (A.M. No. 03-05-01-SC)",
                "source": "db",
            },
        ]
    },
    {
        "roman_num": "XI", "topic_heading": "Judicial Ethics",
        "sub_letter": "B",
        "sub_heading": "Discipline of Members of the Judiciary (Rule 140)",
        "sort_order": 45,
        "provisions": [
            {"statute_id": "ROC", "provision_id": "140-1",  "label": "Rule 140, Sec. 1 – Discipline of judges", "source": "db"},
        ]
    },

    # ──────────────────────────────────────────────────────────────────────────
    # XII. PRACTICAL EXERCISES
    # Syllabus: Promissory Note, Demand Letter, Sale/Lease Contracts, Special Power
    #           of Attorney, Verification and Certification, Affidavits, Notarial Acts,
    #           Motions, Information
    # ──────────────────────────────────────────────────────────────────────────
    {
        "roman_num": "XII", "topic_heading": "Practical Exercises",
        "sub_letter": None, "sub_heading": None,
        "sort_order": 46,
        "provisions": [
            {
                "statute_id": "PRACTICE", "provision_id": "general",
                "label": "Drafting: Promissory Notes, Demand Letters, Sale/Lease Contracts, Special Power of Attorney, Verification and Certification, Affidavits, Notarial Acts, Motions, Information",
                "source": "ai",
            },
        ]
    },

]

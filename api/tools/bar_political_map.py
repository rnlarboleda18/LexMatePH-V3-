"""
Political Law & Public International Law — 2026 Bar Syllabus Topic-to-Provision Map
Case cutoff: June 30, 2025
Weight: Political Law 20%, PIL 5%

source='const'   → Philippine Constitution; provision_id format "art-{roman}-sec-{n}"
source='statute' → RA/PD statutes in DB; provision_id is the statute slug e.g. "ra-7160"
source='roc'     → Rules of Court; provision_id format "rule-{n}-sec-{m}"
source='lawphil' → web URL (string), scraped from LawPhil
source='ai'      → no single codal text; AI synthesises from case law / doctrine

LawPhil URL patterns:
  RA  → https://lawphil.net/statutes/repacts/ra{yr}/ra_{num}_{yr}.html
  PD  → https://lawphil.net/statutes/presdecs/pd{yr}/pd_{num}_{yr}.html
  BP  → https://lawphil.net/statutes/bpblg/bp_{num}_{yr}.html
  EO  → https://lawphil.net/statutes/eos/eo_{num}_{yr}.html
"""

LAWPHIL = "https://lawphil.net"

POLITICAL_MAP = [

    # ══════════════════════════════════════════════════════════════════════════════
    # I. CONSTITUTIONAL LAW
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "I",
        "sub_letter": "A",
        "heading": "Constitutional Law: Nature, Supremacy, and Amendment",
        "provisions": [
            {"source": "const", "provision_id": "art-17-sec-1"},   # Amendments by Congress
            {"source": "const", "provision_id": "art-17-sec-2"},   # Constitutional Convention
            {"source": "const", "provision_id": "art-17-sec-3"},   # People's Initiative
            {"source": "const", "provision_id": "art-17-sec-4"},   # Ratification
            {"source": "lawphil", "url": "https://lawphil.net/consti/cons1987.html"},
            {"source": "ai", "note": "Nature of constitution: written vs unwritten, rigid vs flexible; doctrine of constitutional supremacy; judicial review as check on unconstitutional acts; Marbury v Madison analogy; landmark PH cases on constitutional supremacy (Angara v Electoral Commission)"},
        ],
        "sort_order": 1,
    },
    {
        "roman_num": "I",
        "sub_letter": "B",
        "heading": "Constitutional Law: Separation of Powers, Checks and Balances, and Political Question Doctrine",
        "provisions": [
            {"source": "const", "provision_id": "art-6-sec-1"},    # Legislative power
            {"source": "const", "provision_id": "art-7-sec-1"},    # Executive power
            {"source": "const", "provision_id": "art-8-sec-1"},    # Judicial power
            {"source": "ai", "note": "Doctrine of separation of powers; blending vs separation; checks and balances mechanisms; political question doctrine — Baker v Carr criteria; PH applications: Marcos v Manglapus, Estrada v Desierto; enrolled bill doctrine; enrolled bill vs journal entry rule"},
        ],
        "sort_order": 2,
    },
    {
        "roman_num": "I",
        "sub_letter": "C",
        "heading": "Constitutional Law: State Principles and Policies (Article II)",
        "provisions": [
            {"source": "const", "provision_id": "art-2-sec-1"},    # Democratic republican state
            {"source": "const", "provision_id": "art-2-sec-2"},    # Renunciation of war
            {"source": "const", "provision_id": "art-2-sec-3"},    # Civilian supremacy
            {"source": "const", "provision_id": "art-2-sec-4"},    # Duty to defend state
            {"source": "const", "provision_id": "art-2-sec-5"},    # Maintenance of peace and order
            {"source": "const", "provision_id": "art-2-sec-6"},    # Separation of church and state
            {"source": "const", "provision_id": "art-2-sec-7"},    # Pursuit of independent foreign policy
            {"source": "const", "provision_id": "art-2-sec-8"},    # Freedom from nuclear weapons
            {"source": "const", "provision_id": "art-2-sec-9"},    # Just and dynamic social order
            {"source": "const", "provision_id": "art-2-sec-10"},   # Social justice
            {"source": "const", "provision_id": "art-2-sec-11"},   # Human dignity
            {"source": "const", "provision_id": "art-2-sec-12"},   # Family
            {"source": "const", "provision_id": "art-2-sec-13"},   # Youth
            {"source": "const", "provision_id": "art-2-sec-14"},   # Women
            {"source": "const", "provision_id": "art-2-sec-15"},   # Health
            {"source": "const", "provision_id": "art-2-sec-16"},   # Ecology
            {"source": "const", "provision_id": "art-2-sec-17"},   # Priority for education
            {"source": "const", "provision_id": "art-2-sec-18"},   # Labor
            {"source": "const", "provision_id": "art-2-sec-19"},   # Self-reliant economy
            {"source": "const", "provision_id": "art-2-sec-20"},   # Private sector
            {"source": "const", "provision_id": "art-2-sec-21"},   # Land reform
            {"source": "const", "provision_id": "art-2-sec-22"},   # Indigenous peoples
            {"source": "const", "provision_id": "art-2-sec-23"},   # Non-governmental organizations
            {"source": "const", "provision_id": "art-2-sec-24"},   # Local autonomy
            {"source": "const", "provision_id": "art-2-sec-25"},   # Honest public service
            {"source": "const", "provision_id": "art-2-sec-26"},   # Equality of opportunity
            {"source": "const", "provision_id": "art-2-sec-27"},   # Full public disclosure
            {"source": "const", "provision_id": "art-2-sec-28"},   # Right to information
            {"source": "ai", "note": "Non-self-executing vs self-executing provisions of Article II; justiciability of State principles; doctrine in Tañada v Angara; Oposa v Factoran on intergenerational responsibility; enforceability in litigation"},
        ],
        "sort_order": 3,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # II. FUNDAMENTAL POWERS OF THE STATE
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "II",
        "sub_letter": "A",
        "heading": "Fundamental Powers: Police Power, Eminent Domain, and Taxation — Elements, Tests, and Limits",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-1"},    # Due process & equal protection
            {"source": "const", "provision_id": "art-3-sec-9"},    # Just compensation / taking
            {"source": "const", "provision_id": "art-6-sec-28"},   # Uniform and equitable taxation
            {"source": "ai", "note": "Police power: definition, lawful subjects, lawful means, rational basis / reasonable relation test; eminent domain: elements (necessity, public use, just compensation), expropriability of private property, just compensation determination, writ of possession; taxation power: requisites, situs, exemption; interplay among three powers; leading PH cases: US v Toribio, City of Manila v Laguio, EPZA v Dulay, NPC v CA; regulatory vs compensable taking"},
        ],
        "sort_order": 4,
    },
    {
        "roman_num": "II",
        "sub_letter": "B",
        "heading": "Fundamental Powers: Due Process — Substantive and Procedural (Art. III Sec. 1)",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-1"},
            {"source": "ai", "note": "Substantive due process: void-for-vagueness, overbreadth, legitimate government interest, reasonableness of means; procedural due process: notice and hearing in judicial and administrative contexts; twin requirements in administrative proceedings; cardinal primary rights (Ang Tibay v CIR); hierarchy of rights; mandatory vs directory provisions"},
        ],
        "sort_order": 5,
    },
    {
        "roman_num": "II",
        "sub_letter": "C",
        "heading": "Fundamental Powers: Equal Protection (Art. III Sec. 1)",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-1"},
            {"source": "ai", "note": "Equal protection clause: valid classification requisites (substantial distinctions, germane to law's purpose, applicable to present and future conditions, applies equally to all in the class); rational basis, intermediate scrutiny, strict scrutiny; suspect classifications; PH cases: People v Cayat, Quinto v COMELEC; equal protection vs privilege"},
        ],
        "sort_order": 6,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # III. BILL OF RIGHTS
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "III",
        "sub_letter": "A",
        "heading": "Bill of Rights: Freedom of Expression, Assembly, and Petition (Art. III Secs. 4, 8)",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-4"},    # Freedom of speech/press
            {"source": "const", "provision_id": "art-3-sec-5"},    # Freedom of religion
            {"source": "const", "provision_id": "art-3-sec-8"},    # Right to form associations
            {"source": "ai", "note": "Content-based vs content-neutral regulation; clear and present danger test; balancing of interests; prior restraint and presumption against; overbreadth and facial challenges; libel and sedition; Chavez v Gonzales; ABS-CBN v COMELEC; Soriano v Laguardia; freedom of assembly: permit requirements, Bayan v Ermita; right to petition government"},
        ],
        "sort_order": 7,
    },
    {
        "roman_num": "III",
        "sub_letter": "B",
        "heading": "Bill of Rights: Right Against Unreasonable Searches and Seizures (Art. III Secs. 2–3)",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-2"},    # Search and seizure
            {"source": "const", "provision_id": "art-3-sec-3"},    # Privacy of communications
            {"source": "ai", "note": "Requisites for valid search warrant: probable cause, personal determination by judge, particularity; warrantless searches: search incident to lawful arrest, stop and frisk (Terry doctrine), plain view, moving vehicle, consent, exigent circumstances, customs searches; illegally seized evidence: exclusionary rule; fruit of poisonous tree doctrine; Stonehill v Diokno; People v Aruta; RA 4200 (Anti-Wiretapping); Zulueta v CA on privacy of communications"},
        ],
        "sort_order": 8,
    },
    {
        "roman_num": "III",
        "sub_letter": "C",
        "heading": "Bill of Rights: Rights of the Accused — Miranda Doctrine, Exclusionary Rule (Art. III Secs. 12–17)",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-12"},   # Rights under custodial investigation
            {"source": "const", "provision_id": "art-3-sec-13"},   # Bail
            {"source": "const", "provision_id": "art-3-sec-14"},   # Due process in criminal proceedings
            {"source": "const", "provision_id": "art-3-sec-15"},   # Habeas corpus
            {"source": "const", "provision_id": "art-3-sec-16"},   # Speedy disposition
            {"source": "const", "provision_id": "art-3-sec-17"},   # Non-self-incrimination
            {"source": "statute", "provision_id": "ra-7438"},       # RA 7438 — custodial rights
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1992/ra_7438_1992.html"},
            {"source": "ai", "note": "Miranda warnings: right to remain silent, right to competent and independent counsel preferably of choice, right to be informed; custodial investigation defined; exclusionary rule for uncounseled admissions; bail: matter of right vs discretion; capital offense bail hearing; habeas corpus vs amparo vs habeas data; Speedy trial vs speedy disposition; Caes v IAC; People v Andan; double jeopardy requisites"},
        ],
        "sort_order": 9,
    },
    {
        "roman_num": "III",
        "sub_letter": "D",
        "heading": "Bill of Rights: Liberty of Abode and Right to Travel (Art. III Sec. 6)",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-6"},
            {"source": "ai", "note": "Liberty of abode: may be changed only upon lawful order of court; right to travel: impaired only by court order or law in interest of national security, public safety, public health; immigration lookout bulletin vs HDO vs watch list order; Genuino v De Lima; right of return as fundamental right; Marcos v Manglapus"},
        ],
        "sort_order": 10,
    },
    {
        "roman_num": "III",
        "sub_letter": "E",
        "heading": "Bill of Rights: Right to Privacy (Art. III Sec. 3)",
        "provisions": [
            {"source": "const", "provision_id": "art-3-sec-3"},
            {"source": "statute", "provision_id": "ra-10173"},      # Data Privacy Act
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra2012/ra_10173_2012.html"},
            {"source": "ai", "note": "Zones of privacy; informational privacy; right to be forgotten; constitutional privacy vs statutory privacy (Data Privacy Act); Ople v Torres on national ID; Vivares v St. Theresa's College; writ of habeas data; reasonable expectation of privacy test; Katz v US doctrine applied in Philippine context"},
        ],
        "sort_order": 11,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # IV. CITIZENSHIP AND SUFFRAGE
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "IV",
        "sub_letter": "A",
        "heading": "Citizenship: Modes of Acquisition and Loss (Art. IV)",
        "provisions": [
            {"source": "const", "provision_id": "art-4-sec-1"},    # Citizens of the Philippines
            {"source": "const", "provision_id": "art-4-sec-2"},    # Natural-born citizens
            {"source": "const", "provision_id": "art-4-sec-3"},    # Loss of citizenship
            {"source": "const", "provision_id": "art-4-sec-4"},    # Dual citizenship
            {"source": "statute", "provision_id": "ra-9225"},       # Citizenship Retention and Re-acquisition Act
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra2003/ra_9225_2003.html"},
            {"source": "ai", "note": "Jus soli vs jus sanguinis; modes: birth, naturalization, election, reacquisition; RA 9225 reacquisition; loss by: naturalization in foreign country, express renunciation, subscribing to oath of allegiance; election of citizenship by those born of Filipino mother before 1935 Constitution; foundlings; dual citizenship vs dual allegiance; Bengson v HRET; Valles v COMELEC"},
        ],
        "sort_order": 12,
    },
    {
        "roman_num": "IV",
        "sub_letter": "B",
        "heading": "Suffrage (Art. V)",
        "provisions": [
            {"source": "const", "provision_id": "art-5-sec-1"},    # Suffrage
            {"source": "const", "provision_id": "art-5-sec-2"},    # Absentee voting
            {"source": "statute", "provision_id": "ra-9189"},       # Overseas Absentee Voting Act
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra2003/ra_9189_2003.html"},
            {"source": "ai", "note": "Qualifications: Filipino citizen, 18 years old, resident of PH for at least 1 year, resident of place to vote for 6 months; disqualifications: conviction by final judgment of offense carrying imprisonment ≥1 year, mental incapacity, illiteracy (abolished); absentee voting; party-list system and proportional representation"},
        ],
        "sort_order": 13,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # V. LEGISLATIVE DEPARTMENT
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "V",
        "sub_letter": "A",
        "heading": "Legislative Department: Composition, Qualifications, and Privileges (Art. VI)",
        "provisions": [
            {"source": "const", "provision_id": "art-6-sec-1"},    # Legislative power vested in Congress
            {"source": "const", "provision_id": "art-6-sec-2"},    # Senate composition
            {"source": "const", "provision_id": "art-6-sec-3"},    # Senate qualifications
            {"source": "const", "provision_id": "art-6-sec-4"},    # Senate term
            {"source": "const", "provision_id": "art-6-sec-5"},    # House composition
            {"source": "const", "provision_id": "art-6-sec-6"},    # House qualifications
            {"source": "const", "provision_id": "art-6-sec-7"},    # House term
            {"source": "const", "provision_id": "art-6-sec-8"},    # Electoral tribunals
            {"source": "const", "provision_id": "art-6-sec-9"},    # Commission on Appointments
            {"source": "const", "provision_id": "art-6-sec-10"},   # Vacancies
            {"source": "const", "provision_id": "art-6-sec-11"},   # Privileges — speech or debate
            {"source": "const", "provision_id": "art-6-sec-12"},   # Prohibited offices
            {"source": "const", "provision_id": "art-6-sec-13"},   # Financial interest conflict
            {"source": "const", "provision_id": "art-6-sec-14"},   # SALN of legislators
            {"source": "const", "provision_id": "art-6-sec-15"},   # Session period
            {"source": "const", "provision_id": "art-6-sec-16"},   # Quorum, rules, records
            {"source": "ai", "note": "Party-list system: RA 7941; Banat v COMELEC formula; Atong Paglaum v COMELEC on expanded scope; speech and debate clause; privilege speech vs ordinary utterances; congressional immunity; inhibition and conflict of interest; Pobre v Defensor-Santiago"},
        ],
        "sort_order": 14,
    },
    {
        "roman_num": "V",
        "sub_letter": "B",
        "heading": "Legislative Department: Legislative Process and Limitations on Legislation",
        "provisions": [
            {"source": "const", "provision_id": "art-6-sec-24"},   # Origination of revenue bills
            {"source": "const", "provision_id": "art-6-sec-25"},   # Appropriation — rule on riders
            {"source": "const", "provision_id": "art-6-sec-26"},   # One subject-one title rule; three readings
            {"source": "const", "provision_id": "art-6-sec-27"},   # Presidential veto
            {"source": "const", "provision_id": "art-6-sec-28"},   # Taxation uniformity
            {"source": "const", "provision_id": "art-6-sec-29"},   # Money bills; national treasury
            {"source": "ai", "note": "One subject-one title rule: ABAKADA Guro v Purisima; enrolled bill doctrine vs journal entry rule; bicameral conference committee; pocket veto; item veto on appropriation bills; delegation of legislative power: completeness test and sufficient standard test; Abakada v Ermita on delegated authority; legislative investigations; oversight functions"},
        ],
        "sort_order": 15,
    },
    {
        "roman_num": "V",
        "sub_letter": "C",
        "heading": "Legislative Department: Appropriation, Revenue, and Tariff Bills",
        "provisions": [
            {"source": "const", "provision_id": "art-6-sec-24"},
            {"source": "const", "provision_id": "art-6-sec-25"},
            {"source": "const", "provision_id": "art-6-sec-29"},
            {"source": "ai", "note": "General Appropriations Act; prohibition on appropriation for sectarian purposes; pork barrel jurisprudence: Belgica v Ochoa (PDAF unconstitutional); Araullo v Aquino (DAP); lump-sum appropriations; reenacted budget rule; tariff and customs power of Congress; Congress authority over fiscal matters"},
        ],
        "sort_order": 16,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # VI. EXECUTIVE DEPARTMENT
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "VI",
        "sub_letter": "A",
        "heading": "Executive Department: Qualifications, Election, and Succession (Art. VII)",
        "provisions": [
            {"source": "const", "provision_id": "art-7-sec-1"},    # Executive power
            {"source": "const", "provision_id": "art-7-sec-2"},    # President qualifications
            {"source": "const", "provision_id": "art-7-sec-3"},    # Vice-President
            {"source": "const", "provision_id": "art-7-sec-4"},    # Election of President/VP
            {"source": "const", "provision_id": "art-7-sec-7"},    # Term — 6 years, no re-election
            {"source": "const", "provision_id": "art-7-sec-8"},    # Presidential succession
            {"source": "const", "provision_id": "art-7-sec-9"},    # Vacancy in VP
            {"source": "const", "provision_id": "art-7-sec-10"},   # Incapacity of President
            {"source": "const", "provision_id": "art-7-sec-11"},   # Disability; Cabinet majority
            {"source": "const", "provision_id": "art-7-sec-12"},   # Existence of vacancy — Congress
            {"source": "const", "provision_id": "art-7-sec-13"},   # Prohibitions on President
            {"source": "ai", "note": "Presidential succession: line from VP to Senate President to Speaker; rule on incapacity (Sec. 11); prohibition on re-election; de facto officer doctrine; Estrada v Desierto on constructive resignation"},
        ],
        "sort_order": 17,
    },
    {
        "roman_num": "VI",
        "sub_letter": "B",
        "heading": "Executive Department: Presidential Powers — Appointing, Military, Emergency, Pardoning, Veto",
        "provisions": [
            {"source": "const", "provision_id": "art-7-sec-14"},   # Appointing power
            {"source": "const", "provision_id": "art-7-sec-15"},   # Midnight appointments prohibition
            {"source": "const", "provision_id": "art-7-sec-16"},   # Appointments without CoA confirmation
            {"source": "const", "provision_id": "art-7-sec-17"},   # Control of executive departments
            {"source": "const", "provision_id": "art-7-sec-18"},   # Commander-in-chief; martial law; habeas corpus
            {"source": "const", "provision_id": "art-7-sec-19"},   # Executive clemency / pardoning power
            {"source": "const", "provision_id": "art-7-sec-20"},   # Borrowing power
            {"source": "const", "provision_id": "art-7-sec-21"},   # Treaty concurrence
            {"source": "const", "provision_id": "art-7-sec-22"},   # Budget preparation
            {"source": "const", "provision_id": "art-7-sec-23"},   # State of the Nation Address
            {"source": "ai", "note": "Appointing power: positions requiring CoA confirmation vs those that don't; midnight appointments: De Castro v JBC; control vs supervision distinction; martial law requisites: actual invasion or rebellion + public safety requires it; congressional review of martial law proclamation; revocation by Congress; Lagman v Pimentel; pardoning power scope: conviction by final judgment, exclusion of impeachment cases; types of clemency; emergency powers: delegation to President"},
        ],
        "sort_order": 18,
    },
    {
        "roman_num": "VI",
        "sub_letter": "C",
        "heading": "Executive Department: Executive Privilege, and Executive Agreements vs Treaties",
        "provisions": [
            {"source": "const", "provision_id": "art-7-sec-21"},
            {"source": "const", "provision_id": "art-18-sec-4"},   # EDSA Revolution; treaties in force
            {"source": "ai", "note": "Executive privilege: presidential communications privilege vs deliberative process privilege; Neri v Senate — threshold inquiry; scope and limits; Congress' power to investigate vs executive privilege; executive agreements: binding without Senate concurrence (Bayan Muna v Romulo); distinction from treaties requiring Senate 2/3 concurrence; VFA and EDCA cases; EDCA constitutional validity (Saguisag v Ochoa)"},
        ],
        "sort_order": 19,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # VII. JUDICIAL DEPARTMENT
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "VII",
        "sub_letter": "A",
        "heading": "Judicial Department: Judicial Power and Judicial Review (Art. VIII)",
        "provisions": [
            {"source": "const", "provision_id": "art-8-sec-1"},    # Judicial power definition
            {"source": "const", "provision_id": "art-8-sec-2"},    # Congress cannot deprive SC of jurisdiction
            {"source": "ai", "note": "Expanded concept of judicial power (duty to settle actual controversies involving legally demandable rights); requisites of judicial review: actual controversy, standing, ripeness, prematurity; moot and academic cases; facial vs as-applied challenges; political question doctrine exceptions; ratio decidendi vs obiter dictum; stare decisis; Francisco v House of Representatives on limits of judicial review over impeachment"},
        ],
        "sort_order": 20,
    },
    {
        "roman_num": "VII",
        "sub_letter": "B",
        "heading": "Judicial Department: Supreme Court — Composition, Jurisdiction, and Appointments",
        "provisions": [
            {"source": "const", "provision_id": "art-8-sec-3"},    # Composition
            {"source": "const", "provision_id": "art-8-sec-4"},    # Sessions; en banc vs division
            {"source": "const", "provision_id": "art-8-sec-5"},    # SC jurisdiction
            {"source": "const", "provision_id": "art-8-sec-6"},    # SC administrative supervision
            {"source": "const", "provision_id": "art-8-sec-7"},    # Qualifications
            {"source": "const", "provision_id": "art-8-sec-8"},    # Judicial and Bar Council
            {"source": "const", "provision_id": "art-8-sec-9"},    # Appointment to judiciary
            {"source": "ai", "note": "Original vs appellate jurisdiction of SC; certiorari as discretionary writ; SC power to promulgate rules of procedure; Judicial and Bar Council: composition, function, nomination list; De Castro v JBC (Chief Justice vacancy); SC en banc jurisdiction; doctrine of hierarchy of courts; immediate filing with SC exceptions"},
        ],
        "sort_order": 21,
    },
    {
        "roman_num": "VII",
        "sub_letter": "C",
        "heading": "Judicial Department: Lower Courts and Judicial Independence",
        "provisions": [
            {"source": "const", "provision_id": "art-8-sec-10"},   # Congress creates lower courts
            {"source": "const", "provision_id": "art-8-sec-11"},   # Security of tenure of judges
            {"source": "const", "provision_id": "art-8-sec-12"},   # Members of judiciary — no designation
            {"source": "const", "provision_id": "art-8-sec-13"},   # Salary non-diminution
            {"source": "const", "provision_id": "art-8-sec-14"},   # Decisions: facts and law stated
            {"source": "const", "provision_id": "art-8-sec-15"},   # Periods for decisions
            {"source": "const", "provision_id": "art-8-sec-16"},   # Annual report
            {"source": "ai", "note": "Security of tenure: removal only by impeachment for SC justices; administrative cases for lower court judges; independence of judiciary from executive and legislative interference; Bengzon v Drilon on salary non-diminution; requirement of written decisions; periods for resolution"},
        ],
        "sort_order": 22,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # VIII. CONSTITUTIONAL COMMISSIONS
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "VIII",
        "sub_letter": "A",
        "heading": "Constitutional Commissions: Civil Service Commission (Art. IX-B)",
        "provisions": [
            {"source": "const", "provision_id": "art-9-b-sec-1"},  # CSC composition
            {"source": "const", "provision_id": "art-9-b-sec-2"},  # CSC coverage
            {"source": "const", "provision_id": "art-9-b-sec-3"},  # Appointments to civil service
            {"source": "const", "provision_id": "art-9-b-sec-4"},  # No partisan political activity
            {"source": "const", "provision_id": "art-9-b-sec-5"},  # Right to self-organization
            {"source": "const", "provision_id": "art-9-b-sec-6"},  # Temporary employees
            {"source": "statute", "provision_id": "ra-2260"},       # Civil Service Act (as amended by EO 292)
            {"source": "ai", "note": "Career vs non-career service; competitive vs non-competitive positions; security of tenure in civil service; prohibitions on political activity; right to self-organize (no right to strike); appointments: permanent vs temporary vs designations; eligibility requirements; RA 6713 (Code of Conduct and Ethical Standards); CSC jurisdiction over administrative cases"},
        ],
        "sort_order": 23,
    },
    {
        "roman_num": "VIII",
        "sub_letter": "B",
        "heading": "Constitutional Commissions: COMELEC (Art. IX-C)",
        "provisions": [
            {"source": "const", "provision_id": "art-9-c-sec-1"},  # COMELEC composition
            {"source": "const", "provision_id": "art-9-c-sec-2"},  # COMELEC powers
            {"source": "const", "provision_id": "art-9-c-sec-3"},  # Decisions: division then en banc
            {"source": "const", "provision_id": "art-9-c-sec-4"},  # Deputization of law enforcement
            {"source": "const", "provision_id": "art-9-c-sec-5"},  # Registration of political parties
            {"source": "const", "provision_id": "art-9-c-sec-6"},  # Free and open party system
            {"source": "const", "provision_id": "art-9-c-sec-7"},  # No pardon/amnesty for election offenses
            {"source": "ai", "note": "COMELEC jurisdiction over election contests; pre-proclamation vs post-proclamation; election protest vs quo warranto; COMELEC en banc jurisdiction for motions for reconsideration; Loong v COMELEC; Sumulong v COMELEC; automated elections; RA 8436 as amended by RA 9369; jurisdiction over party-list organizations; campaign finance rules"},
        ],
        "sort_order": 24,
    },
    {
        "roman_num": "VIII",
        "sub_letter": "C",
        "heading": "Constitutional Commissions: Commission on Audit (Art. IX-D)",
        "provisions": [
            {"source": "const", "provision_id": "art-9-d-sec-1"},  # COA composition
            {"source": "const", "provision_id": "art-9-d-sec-2"},  # COA powers and functions
            {"source": "const", "provision_id": "art-9-d-sec-3"},  # Salary non-diminution
            {"source": "ai", "note": "COA general audit authority over government funds and property; government-owned and controlled corporations (GOCCs); post-audit vs pre-audit; disallowance proceedings; notice of disallowance; liability of approving and certifying officers; Madera v COA (good faith return rule); Uy v COA; COA decisions appealable to SC via Rule 64"},
        ],
        "sort_order": 25,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # IX. LOCAL GOVERNMENT
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "IX",
        "sub_letter": "A",
        "heading": "Local Government: Local Autonomy and Devolution (RA 7160 — LGC)",
        "provisions": [
            {"source": "const", "provision_id": "art-10-sec-1"},   # LGU creation
            {"source": "const", "provision_id": "art-10-sec-2"},   # Territorial and political subdivisions
            {"source": "const", "provision_id": "art-10-sec-3"},   # LGU legislature
            {"source": "const", "provision_id": "art-10-sec-4"},   # Organic act
            {"source": "const", "provision_id": "art-10-sec-5"},   # Taxing power
            {"source": "const", "provision_id": "art-10-sec-6"},   # Just share in national taxes
            {"source": "const", "provision_id": "art-10-sec-7"},   # Equitable share in national wealth
            {"source": "const", "provision_id": "art-10-sec-10"},  # Creation of LGUs
            {"source": "statute", "provision_id": "ra-7160"},       # Local Government Code
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1991/ra_7160_1991.html"},
            {"source": "ai", "note": "Devolution of national government functions to LGUs; principle of local autonomy; Gancho-on v Arellano (nature of local autonomy); Limbona v Mangelin; ultra vires acts of LGUs; creation, division, merger, abolition of LGUs (plebiscite requirement); IRA / national tax allotment: Mandanas v Ochoa (expanded base)"},
        ],
        "sort_order": 26,
    },
    {
        "roman_num": "IX",
        "sub_letter": "B",
        "heading": "Local Government: LGU Powers — Taxing, Eminent Domain, Police Power",
        "provisions": [
            {"source": "const", "provision_id": "art-10-sec-5"},
            {"source": "statute", "provision_id": "ra-7160"},
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1991/ra_7160_1991.html"},
            {"source": "ai", "note": "LGC Sec. 130-233 (local taxation power); LGC Sec. 19 (eminent domain); LGU police power as general welfare clause (LGC Sec. 16); double taxation; limitations on LGU taxing power; national tax exemptions not applicable to local taxes; Pelizloy Realty v Province of Benguet; Manila Electric Company v Province of Laguna; LGU expropriation: conditions, just compensation"},
        ],
        "sort_order": 27,
    },
    {
        "roman_num": "IX",
        "sub_letter": "C",
        "heading": "Local Government: Recall, Term Limits, and Local Legislative Process",
        "provisions": [
            {"source": "const", "provision_id": "art-10-sec-8"},   # Term limits for elective local officials
            {"source": "statute", "provision_id": "ra-7160"},
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1991/ra_7160_1991.html"},
            {"source": "ai", "note": "Term limits: 3 consecutive terms for local officials; three-term limit rule: Lonzanida v COMELEC; Borja v COMELEC; what constitutes a term; recall procedure: grounds, period, COMELEC supervision; local legislative process: Sanggunian; ordinance vs resolution; review by higher Sanggunian; barangay governance; Liga ng mga Barangay"},
        ],
        "sort_order": 28,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # X. ACCOUNTABILITY OF PUBLIC OFFICERS
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "X",
        "sub_letter": "A",
        "heading": "Accountability of Public Officers: Impeachment (Art. XI)",
        "provisions": [
            {"source": "const", "provision_id": "art-11-sec-1"},   # Public office is public trust
            {"source": "const", "provision_id": "art-11-sec-2"},   # Impeachable officers
            {"source": "const", "provision_id": "art-11-sec-3"},   # Impeachment process
            {"source": "const", "provision_id": "art-11-sec-4"},   # Senate as impeachment court
            {"source": "const", "provision_id": "art-11-sec-5"},   # Judgment in impeachment
            {"source": "ai", "note": "Impeachable officers: President, VP, SC Justices, constitutional commission members, Ombudsman; grounds: culpable violation of Constitution, treason, bribery, graft and corruption, other high crimes, betrayal of public trust; one-year bar rule; Francisco v House of Representatives on initiation; political vs judicial question in impeachment; Sereno v Republic (quo warranto as alternative)"},
        ],
        "sort_order": 29,
    },
    {
        "roman_num": "X",
        "sub_letter": "B",
        "heading": "Accountability of Public Officers: Ombudsman (Art. XI Secs. 5–14; RA 6770)",
        "provisions": [
            {"source": "const", "provision_id": "art-11-sec-5"},   # Creation of Ombudsman
            {"source": "const", "provision_id": "art-11-sec-6"},   # Composition
            {"source": "const", "provision_id": "art-11-sec-7"},   # Qualifications
            {"source": "const", "provision_id": "art-11-sec-8"},   # Term of office
            {"source": "const", "provision_id": "art-11-sec-9"},   # Prohibited activities
            {"source": "const", "provision_id": "art-11-sec-10"},  # Fiscal autonomy
            {"source": "const", "provision_id": "art-11-sec-11"},  # Deputies
            {"source": "const", "provision_id": "art-11-sec-12"},  # Powers and functions
            {"source": "const", "provision_id": "art-11-sec-13"},  # Ombudsman actions on complaints
            {"source": "const", "provision_id": "art-11-sec-14"},  # Salary and qualifications
            {"source": "statute", "provision_id": "ra-6770"},
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1989/ra_6770_1989.html"},
            {"source": "ai", "note": "Ombudsman jurisdiction over public officers; preventive suspension; administrative vs criminal cases; Sec. 27 of RA 6770 on finality (partially struck down in Fabian v Desierto); appeal from Ombudsman decisions: Court of Appeals (administrative); Sandiganbayan (criminal); Ombudsman's power to investigate military; Carpio-Morales v CA on CA jurisdiction"},
        ],
        "sort_order": 30,
    },
    {
        "roman_num": "X",
        "sub_letter": "C",
        "heading": "Accountability of Public Officers: Sandiganbayan (PD 1606; RA 8249)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-1606"},
            {"source": "lawphil", "url": "https://lawphil.net/statutes/presdecs/pd1977/pd_1606_1977.html"},
            {"source": "statute", "provision_id": "ra-8249"},
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1997/ra_8249_1997.html"},
            {"source": "ai", "note": "Sandiganbayan jurisdiction: public officials with salary grade 27 and above; specific offices regardless of grade; principal vs accessory offenses; concurrent jurisdiction with regional trial courts; penalties under RA 3019; Lacson v Executive Secretary on jurisdictional thresholds; consolidation of cases; appeals from Sandiganbayan to SC via Rule 45"},
        ],
        "sort_order": 31,
    },
    {
        "roman_num": "X",
        "sub_letter": "D",
        "heading": "Accountability of Public Officers: Anti-Graft and Corrupt Practices (RA 3019)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-3019"},
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1960/ra_3019_1960.html"},
            {"source": "ai", "note": "Prohibited acts under RA 3019 Sec. 3: persuading another officer, requesting or receiving gifts, entering into manifestly disadvantageous contracts, interventions, financial interest in business; gross inexcusable negligence; forfeiture of ill-gotten wealth; prescriptive period; suspension pendente lite; Republic v Sandiganbayan; Miriam Defensor-Santiago v Sandiganbayan; RA 6713 Code of Conduct compatibility"},
        ],
        "sort_order": 32,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XI. NATIONAL ECONOMY AND PATRIMONY
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XI",
        "sub_letter": "A",
        "heading": "National Economy and Patrimony: Regalian Doctrine and Natural Resources (Art. XII)",
        "provisions": [
            {"source": "const", "provision_id": "art-12-sec-1"},   # Goals of national economy
            {"source": "const", "provision_id": "art-12-sec-2"},   # Regalian doctrine; natural resources
            {"source": "const", "provision_id": "art-12-sec-3"},   # Lands of public domain classification
            {"source": "const", "provision_id": "art-12-sec-4"},   # Congress — alienable agricultural land
            {"source": "const", "provision_id": "art-12-sec-5"},   # Ancestral domain
            {"source": "ai", "note": "Jura regalia; Carino v Insular Government (native title exception); Heirs of Malabanan v Republic on acquisitive prescription of public lands; classification of lands of public domain: agricultural, forest, mineral, national parks; only agricultural lands can be alienated; fishing areas; DENR jurisdiction; mining rights; service contracts under Art. XII Sec. 2; La Bugal-B'laan v Ramos on FTAA validity"},
        ],
        "sort_order": 33,
    },
    {
        "roman_num": "XI",
        "sub_letter": "B",
        "heading": "National Economy and Patrimony: Nationalization, Foreign Equity Restrictions, and Franchise Requirements",
        "provisions": [
            {"source": "const", "provision_id": "art-12-sec-10"},  # Preferential rights for Filipinos
            {"source": "const", "provision_id": "art-12-sec-11"},  # Franchises, certificates, authorizations
            {"source": "const", "provision_id": "art-12-sec-12"},  # Practice of professions
            {"source": "const", "provision_id": "art-12-sec-13"},  # Mandatory provisions for public utilities
            {"source": "const", "provision_id": "art-12-sec-14"},  # Filipino preference in capital
            {"source": "const", "provision_id": "art-12-sec-15"},  # Technical education
            {"source": "const", "provision_id": "art-12-sec-16"},  # Organization of private corporations
            {"source": "const", "provision_id": "art-12-sec-17"},  # Takeover of utilities in national emergency
            {"source": "const", "provision_id": "art-12-sec-18"},  # Public utilities under Filipino control
            {"source": "const", "provision_id": "art-12-sec-19"},  # Combination in restraint of trade
            {"source": "const", "provision_id": "art-12-sec-20"},  # BSP — central monetary authority
            {"source": "const", "provision_id": "art-12-sec-21"},  # Foreign loans
            {"source": "ai", "note": "60-40 Filipino-foreign equity rule for public utilities; Heirs of Fernando v Republic; public utility definition post-RA 11659; Gamboa v Teves on capital definition (60% voting shares); anti-dummy law (CA 108); franchise granted by Congress; congressional franchise requirement and its limitations; FDI restrictions; retail trade nationalization"},
        ],
        "sort_order": 34,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XII. SOCIAL JUSTICE AND HUMAN RIGHTS
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XII",
        "sub_letter": "A",
        "heading": "Social Justice and Human Rights: Commission on Human Rights (Art. XIII)",
        "provisions": [
            {"source": "const", "provision_id": "art-13-sec-17"},  # CHR creation
            {"source": "const", "provision_id": "art-13-sec-18"},  # CHR powers
            {"source": "ai", "note": "CHR: investigatory — not adjudicatory body; no power to award damages (Simon v CHR); CHR jurisdiction limited to civil and political rights violations by state; cannot investigate violations by private parties; recommendatory functions; annual report to Congress; CHR vs human rights bodies distinction"},
        ],
        "sort_order": 35,
    },
    {
        "roman_num": "XII",
        "sub_letter": "B",
        "heading": "Social Justice and Human Rights: Labor, Agrarian Reform, and Urban Land Reform (Art. XIII)",
        "provisions": [
            {"source": "const", "provision_id": "art-13-sec-1"},   # Congress to prioritize agrarian reform
            {"source": "const", "provision_id": "art-13-sec-2"},   # Agrarian and natural resources reform
            {"source": "const", "provision_id": "art-13-sec-3"},   # Labor rights
            {"source": "const", "provision_id": "art-13-sec-4"},   # Agrarian reform program
            {"source": "const", "provision_id": "art-13-sec-5"},   # Urban land reform
            {"source": "const", "provision_id": "art-13-sec-6"},   # People's organizations
            {"source": "const", "provision_id": "art-13-sec-7"},   # Right to organize
            {"source": "const", "provision_id": "art-13-sec-8"},   # Right to strike
            {"source": "const", "provision_id": "art-13-sec-9"},   # DOLE
            {"source": "const", "provision_id": "art-13-sec-10"},  # Rural development
            {"source": "const", "provision_id": "art-13-sec-14"},  # Women
            {"source": "const", "provision_id": "art-13-sec-16"},  # People's organizations in governance
            {"source": "statute", "provision_id": "ra-6657"},       # CARP (as amended by RA 9700)
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1988/ra_6657_1988.html"},
            {"source": "ai", "note": "CARP coverage; just compensation for agricultural lands taken; DAR administrative proceedings; conversion of agricultural land; security of tenure of tenants; urban land reform; urban poor rights to housing (RA 7279); right to organize and strike — not absolute; government employees: right to organize but not to strike; legitimate labor organizations"},
        ],
        "sort_order": 36,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XIII. EDUCATION, SCIENCE, TECHNOLOGY, ARTS, CULTURE AND SPORTS
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XIII",
        "sub_letter": "A",
        "heading": "Education, Science, Technology, Arts, Culture, and Sports (Art. XIV)",
        "provisions": [
            {"source": "const", "provision_id": "art-14-sec-1"},   # Free public education
            {"source": "const", "provision_id": "art-14-sec-2"},   # State shall establish complete integrated education system
            {"source": "const", "provision_id": "art-14-sec-3"},   # Goals of national education
            {"source": "const", "provision_id": "art-14-sec-4"},   # Educational institutions
            {"source": "const", "provision_id": "art-14-sec-5"},   # Academic freedom
            {"source": "const", "provision_id": "art-14-sec-6"},   # Filipino as national language
            {"source": "const", "provision_id": "art-14-sec-7"},   # Official languages
            {"source": "const", "provision_id": "art-14-sec-14"},  # Protection of Filipino artists
            {"source": "const", "provision_id": "art-14-sec-17"},  # Science and technology
            {"source": "const", "provision_id": "art-14-sec-19"},  # Sports
            {"source": "ai", "note": "Academic freedom: institution's right to determine who may teach, what to teach, how to teach, and who may be admitted; Garcia v Faculty Admission Committee; University of San Agustin v CA; mandatory free education (K-12 per RA 10533); DepEd, CHED, TESDA triangle; ownership restrictions on educational institutions; religion in private schools"},
        ],
        "sort_order": 37,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XIV. AUTONOMY AND INDIGENOUS PEOPLES
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XIV",
        "sub_letter": "A",
        "heading": "Autonomy and Indigenous Peoples: Autonomous Regions (Art. X)",
        "provisions": [
            {"source": "const", "provision_id": "art-10-sec-15"},  # Creation of autonomous regions
            {"source": "const", "provision_id": "art-10-sec-16"},  # Autonomous region legislative power
            {"source": "const", "provision_id": "art-10-sec-17"},  # National government retains power over certain matters
            {"source": "const", "provision_id": "art-10-sec-18"},  # Organic act for autonomous regions
            {"source": "const", "provision_id": "art-10-sec-19"},  # Integration of barangays into municipalities
            {"source": "const", "provision_id": "art-10-sec-20"},  # Autonomous region legislative authority
            {"source": "const", "provision_id": "art-10-sec-21"},  # Preservation of peace and order
            {"source": "statute", "provision_id": "ra-9054"},       # ARMM Organic Act
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra2001/ra_9054_2001.html"},
            {"source": "ai", "note": "Bangsamoro Organic Law (RA 11054) replacing ARMM with BARMM; Plebiscite requirement; Abakada v Purisima on autonomy; powers retained by national government (foreign affairs, national defense, postal service, coinage, immigration, etc.); intergovernmental relations; Cordillera autonomy"},
        ],
        "sort_order": 38,
    },
    {
        "roman_num": "XIV",
        "sub_letter": "B",
        "heading": "Autonomy and Indigenous Peoples: Indigenous Cultural Communities / Indigenous Peoples (RA 8371 — IPRA)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-8371"},
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra1997/ra_8371_1997.html"},
            {"source": "const", "provision_id": "art-12-sec-5"},   # Ancestral domain
            {"source": "const", "provision_id": "art-2-sec-22"},   # Indigenous peoples recognition
            {"source": "ai", "note": "IPRA: ancestral domain vs ancestral land; Certificate of Ancestral Domain Title (CADT) vs Certificate of Ancestral Land Title (CALT); free, prior, and informed consent (FPIC); indigenous political structures; customary law; National Commission on Indigenous Peoples (NCIP); Cruz v Secretary of Environment (IPRA constitutionality — no majority struck it down); Carino v Insular Government as native title foundation"},
        ],
        "sort_order": 39,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XV. NATURE AND SOURCES OF INTERNATIONAL LAW (PUBLIC INTERNATIONAL LAW)
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XV",
        "sub_letter": "A",
        "heading": "Public International Law: Nature and Sources — Treaties, Custom, General Principles (ICJ Statute Art. 38)",
        "provisions": [
            {"source": "ai", "note": "ICJ Statute Article 38(1) sources: (a) international conventions/treaties; (b) international custom as evidence of general practice accepted as law; (c) general principles of law recognised by civilized nations; (d) judicial decisions and teachings as subsidiary means; jus cogens norms (peremptory norms, non-derogable); erga omnes obligations; opinio juris sive necessitatis; persistent objector doctrine; soft law vs hard law; relationship between sources: lex specialis, lex posterior"},
        ],
        "sort_order": 40,
    },
    {
        "roman_num": "XV",
        "sub_letter": "B",
        "heading": "Public International Law: Relationship of International Law and Municipal Law — Philippine Practice",
        "provisions": [
            {"source": "const", "provision_id": "art-2-sec-2"},    # Adoption of generally accepted principles of international law
            {"source": "const", "provision_id": "art-7-sec-21"},   # Treaty concurrence — Senate 2/3
            {"source": "ai", "note": "Monism vs dualism; transformation doctrine vs incorporation doctrine; Art. II Sec. 2 adopts incorporation doctrine for customary international law; treaties require Senate concurrence (Art. VII Sec. 21) for binding municipal effect; self-executing vs non-self-executing treaties; Mijares v Rañada on foreign judgments; Tañada v Angara (WTO Agreement constitutionality); Pharmaceutical and Health Care Association v Duque III; Bayan Muna v Romulo (executive agreements); VFA validity"},
        ],
        "sort_order": 41,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XVI. STATE RESPONSIBILITY AND JURISDICTION
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XVI",
        "sub_letter": "A",
        "heading": "Public International Law: Statehood — Montevideo Criteria",
        "provisions": [
            {"source": "ai", "note": "Montevideo Convention on Rights and Duties of States (1933) Art. 1: (1) permanent population, (2) defined territory, (3) effective government, (4) capacity to enter international relations; declaratory vs constitutive theory of recognition; recognition of states vs recognition of governments; self-determination; failed states; belligerency recognition; succession of states; distinction from international organizations"},
        ],
        "sort_order": 42,
    },
    {
        "roman_num": "XVI",
        "sub_letter": "B",
        "heading": "Public International Law: Jurisdiction — Territory, Nationality, Effects, Protective, Universal",
        "provisions": [
            {"source": "ai", "note": "Territorial jurisdiction: objective and subjective; nationality/active personality principle; passive personality principle; protective principle (acts threatening state security); effects doctrine (Lotus case); universal jurisdiction: piracy, genocide, war crimes, crimes against humanity, torture; Cutting Case; Lotus Case (PCIJ 1927); extradition vs deportation; aut dedere aut judicare; Philippine Extradition Law (PD 1069)"},
        ],
        "sort_order": 43,
    },
    {
        "roman_num": "XVI",
        "sub_letter": "C",
        "heading": "Public International Law: State Responsibility, Diplomatic Protection, and Espousal of Claims",
        "provisions": [
            {"source": "ai", "note": "ILC Articles on State Responsibility (2001): internationally wrongful act = breach of international obligation attributable to state; elements of attribution: organs, ultra vires acts, private conduct; circumstances precluding wrongfulness; reparations: restitution, compensation, satisfaction; diplomatic protection: nationality of claims, genuine link (Nottebohm case), continuous nationality rule; exhaustion of local remedies rule; espousal of claims; Calvo clause; hull formula vs appropriate standard of compensation for expropriation"},
        ],
        "sort_order": 44,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XVII. TREATY LAW
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XVII",
        "sub_letter": "A",
        "heading": "Public International Law: Vienna Convention on the Law of Treaties (1969) — Formation, Reservations, Invalidity, Termination",
        "provisions": [
            {"source": "ai", "note": "VCLT 1969: definition of treaty (Art. 2); full powers (Arts. 7-8); adoption and authentication (Arts. 9-10); consent to be bound: signature, ratification, accession (Arts. 11-17); entry into force (Art. 24); reservations: definition, permissibility, effect (Arts. 19-23); interpretation: ordinary meaning, context, object and purpose, subsequent practice (Arts. 31-32); pacta sunt servanda (Art. 26); non-retroactivity (Art. 28); invalidity: error, fraud, corruption, coercion, jus cogens conflict (Arts. 46-53); termination: withdrawal, suspension, rebus sic stantibus (Arts. 54-64); severability"},
        ],
        "sort_order": 45,
    },
    {
        "roman_num": "XVII",
        "sub_letter": "B",
        "heading": "Public International Law: Philippine Treaty-Making Practice (Art. VII Sec. 21; Art. XVIII Sec. 4)",
        "provisions": [
            {"source": "const", "provision_id": "art-7-sec-21"},
            {"source": "const", "provision_id": "art-18-sec-4"},
            {"source": "ai", "note": "Senate concurrence requirement: 2/3 of all Senate members for treaties; distinction from executive agreements (Bayan Muna v Romulo); executive power to enter executive agreements without Senate concurrence; Saguisag v Ochoa (EDCA as executive agreement — valid); ASEAN Charter ratification; Vienna Convention on Consular Relations and Diplomatic Relations as treaties in force; Art. XVIII Sec. 4 — treaties from previous government remain valid unless revoked"},
        ],
        "sort_order": 46,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XVIII. INTERNATIONAL HUMAN RIGHTS AND HUMANITARIAN LAW
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XVIII",
        "sub_letter": "A",
        "heading": "Public International Law: International Human Rights — UDHR, ICCPR, ICESCR, Treaty Body System",
        "provisions": [
            {"source": "ai", "note": "UDHR (1948): non-binding but customary in parts; ICCPR (1966): civil and political rights — derogable (Art. 4) and non-derogable rights; ICESCR (1966): economic, social, cultural rights — progressive realization; Optional Protocols: individual complaint mechanisms; treaty body system: Human Rights Committee (HRC), CESCR, CAT, CEDAW, CRC, CERD; UPR under UNHRC; Philippines' international human rights obligations; jus cogens rights: prohibition on torture, slavery, genocide"},
        ],
        "sort_order": 47,
    },
    {
        "roman_num": "XVIII",
        "sub_letter": "B",
        "heading": "Public International Law: International Humanitarian Law — Geneva Conventions and War Crimes",
        "provisions": [
            {"source": "ai", "note": "IHL sources: Hague Law (conduct of hostilities) + Geneva Law (protection of victims); four Geneva Conventions (1949): GC I (wounded on land), GC II (wounded at sea), GC III (POWs), GC IV (civilians); Additional Protocols I and II (1977); Common Article 3 (non-international armed conflicts); principles: distinction, proportionality, military necessity, precaution, prohibition of unnecessary suffering; grave breaches as war crimes; Rome Statute: ICC jurisdiction over war crimes, crimes against humanity, genocide, aggression; individual criminal responsibility; command responsibility; PH withdrawal from ICC (2019) — effects on pending investigations; RA 9851 (IHL Act)"},
        ],
        "sort_order": 48,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XIX. LAW OF THE SEA
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XIX",
        "sub_letter": "A",
        "heading": "Public International Law: UNCLOS — Baselines, Territorial Sea, EEZ, Continental Shelf, High Seas",
        "provisions": [
            {"source": "statute", "provision_id": "ra-9522"},       # Philippine Baseline Law (UNCLOS)
            {"source": "lawphil", "url": "https://lawphil.net/statutes/repacts/ra2009/ra_9522_2009.html"},
            {"source": "ai", "note": "UNCLOS III (1982): maritime zones — internal waters, archipelagic waters, territorial sea (12 nm), contiguous zone (24 nm), exclusive economic zone (200 nm), continental shelf, high seas, Area (deep seabed); archipelagic state: straight archipelagic baselines (RA 9522 amending RA 3046); innocent passage vs transit passage; EEZ rights: sovereign rights for exploration, exploitation; freedom of the high seas; CLCS for continental shelf extensions; Regime of Islands (Art. 121 UNCLOS)"},
        ],
        "sort_order": 49,
    },
    {
        "roman_num": "XIX",
        "sub_letter": "B",
        "heading": "Public International Law: South China Sea Arbitration (Philippines v. China, PCA Case No. 2013-19, 2016)",
        "provisions": [
            {"source": "ai", "note": "South China Sea Arbitration Award (12 July 2016): PCA Annex VII tribunal; China's nine-dash line claim rejected as having no legal basis under UNCLOS; Scarborough Shoal (Bajo de Masinloc) as rock under Art. 121(3) — no EEZ; Spratlys features as rocks or low-tide elevations; China's interference with Philippine fishing rights at Scarborough Shoal violated UNCLOS; China's island-building activities in PH EEZ; China's non-participation — tribunal found jurisdiction; Award is final and binding under UNCLOS; PH policy of 'quiet diplomacy' post-2016; implications for PH maritime rights in West Philippine Sea"},
        ],
        "sort_order": 50,
    },

    # ══════════════════════════════════════════════════════════════════════════════
    # XX. INTERNATIONAL ORGANIZATIONS AND DISPUTE SETTLEMENT
    # ══════════════════════════════════════════════════════════════════════════════

    {
        "roman_num": "XX",
        "sub_letter": "A",
        "heading": "Public International Law: UN Charter — Membership, Principal Organs, Security Council Veto",
        "provisions": [
            {"source": "ai", "note": "UN Charter (1945): purposes and principles (Art. 1-2); prohibition on use of force (Art. 2(4)); self-defense (Art. 51); six principal organs: General Assembly, Security Council, Secretariat, ICJ, ECOSOC, Trusteeship Council; Security Council: 5 permanent members (P5) + 10 non-permanent; veto power of P5 in non-procedural matters; Chapter VI (pacific settlement) vs Chapter VII (enforcement measures); collective security; UN peacekeeping; reforms of UN Security Council; Philippine UN membership and obligations"},
        ],
        "sort_order": 51,
    },
    {
        "roman_num": "XX",
        "sub_letter": "B",
        "heading": "Public International Law: ICJ — Jurisdiction and Advisory Opinions; Other Dispute Settlement Mechanisms",
        "provisions": [
            {"source": "ai", "note": "ICJ: principal judicial organ of UN; contentious jurisdiction: both states must consent — optional clause (Art. 36(2) ICJ Statute), compromissory clauses in treaties, special agreement; forum prorogatum; preliminary objections; admissibility and jurisdiction distinguished; provisional measures; advisory jurisdiction: UNGA, UNSC, authorized UN organs/agencies; advisory opinions non-binding but authoritative; other mechanisms: PCA (arbitration), ITLOS (law of the sea), ICC, WTO DSB, investment arbitration (ICSID); conciliation, mediation, good offices; ASEAN dispute settlement (TAC); ius standi in international courts; exhaustion of local remedies"},
        ],
        "sort_order": 52,
    },
]

"""
2026 Philippine Bar Examinations — Official Syllabus Reference
Cutoff date: June 30, 2025 (only laws, rules, and jurisprudence up to this date are examinable)

Subjects and weights:
  Political Law and Public International Law        15%
  Labor Law and Social Legislation                  10%
  Civil Law and Land Titles and Deeds               20%
  Criminal Law                                      10%
  Remedial Law, Legal and Judicial Ethics           25%
  (Taxation Law and Mercantile Law syllabi pending) 20%
"""

BAR_EXAM_YEAR = 2026
JURISPRUDENCE_CUTOFF = "June 30, 2025"

SUBJECTS: dict[str, dict] = {

    "political_law": {
        "title": "Political Law and Public International Law",
        "weight_pct": 15,
        "topics": [
            "Basic Concepts (Constitution, Amendment, Revision, Sovereignty, State Immunity, Separation of Powers, Fundamental Powers)",
            "National Territory (Archipelagic Doctrine, Maritime Zones)",
            "Citizenship (Natural-born, Naturalized, Dual Citizenship, RA 9225)",
            "Legislative Department (Legislative Power, Party-list, Impeachment, Lawmaking Process)",
            "Executive Department (Powers of the President: Appointment, Control, Emergency, Commander-in-Chief, Pardoning, Diplomatic)",
            "Judicial Department (Judicial Review, Political Question Doctrine, Supreme Court Composition and Jurisdiction)",
            "Constitutional Commissions (COMELEC, COA, CSC)",
            "Constitutional Rights (Due Process, Equal Protection, Bill of Rights, Searches and Seizures, Privacy, Free Speech, Religion, Custodial Investigation, Writs)",
            "National Economy and Patrimony (Regalian Doctrine, RA 11659, Ancestral Domain RA 8371)",
            "Administrative Law (Quasi-legislative and Quasi-judicial Powers, Exhaustion of Administrative Remedies)",
            "Law on Public Officers (Civil Service, Accountability, Ombudsman, Sandiganbayan, Condonation Doctrine)",
            "Election Law (Suffrage, Candidacy, Campaign, Electoral Tribunals, COMELEC Jurisdiction)",
            "Local Governments (Local Autonomy, LGU Powers, Recall, Term Limits)",
            "Public International Law (Sources, Treaty Law, State Responsibility, Extradition, International Human Rights Law, IHL, Law of the Sea)",
        ],
        "key_statutes": [
            "1987 Constitution", "RA 9225 (Citizenship Retention)", "RA 10752 (Eminent Domain)",
            "RA 11659 (New Public Service Act)", "RA 8371 (IPRA)", "RA 10173 (Data Privacy Act)",
            "RA 6770 (Ombudsman Act)", "EO 2 s.2016 (Freedom of Information)",
        ],
        "notable_cases": [
            "Republic v. Pasig Rizal Co. Inc., G.R. No. 213207, February 15, 2022 (Regalian Doctrine)",
        ],
    },

    "labor_law": {
        "title": "Labor Law and Social Legislation",
        "weight_pct": 10,
        "topics": [
            "Basic Principles (ILO Ratifications, 1987 Constitution, Labor Code, Social Justice)",
            "Recruitment and Placement (Local Employment, Overseas Employment RA 8042, Illegal Recruitment)",
            "Employment Relationship (Four-fold Test, Labor-only Contracting, DO 174 s.2017, Kinds of Employment)",
            "Labor Standards (Hours of Work, Flexible Work RA 11165, Wages, Leaves, Telecommuting, Special Workers)",
            "Management Prerogative (Transfer, Discipline, Post-employment Restrictions, Anti-Discrimination)",
            "Labor Relations (Right to Self-organization, Bargaining Unit, CBA, Unfair Labor Practice, Strikes/Lockouts)",
            "Termination of Employment (Just Causes, Authorized Causes, Due Process, Constructive Dismissal, Illegal Dismissal Reliefs)",
            "Social Legislation (SSS RA 11199, GSIS RA 8291, Seafarers RA 12021, Mental Health in Workplace)",
            "Labor Adjudication (NLRC, DOLE, NCMB, Certiorari, Single-Entry Approach RA 10396)",
        ],
        "key_statutes": [
            "Labor Code of the Philippines", "RA 8042 as amended (Migrant Workers Act)",
            "RA 11199 (Social Security Act)", "RA 8291 (GSIS Act)", "RA 12021 (Magna Carta of Filipino Seafarers)",
            "RA 11165 (Telecommuting Act)", "RA 10361 (Kasambahay Law)",
            "RA 11360 (Service Charge Law)", "DO 174 s.2017 (Contracting/Subcontracting)",
            "DO 147 s.2015 (Termination of Employment)", "DO 242 s.2024",
        ],
        "notable_cases": [],
    },

    "civil_law": {
        "title": "Civil Law and Land Titles and Deeds",
        "weight_pct": 20,
        "topics": [
            "Effect and Application of Laws (NCC Arts. 1-18, Operative Fact Doctrine, Conflict of Laws: Lex Nationalii, Lex Rei Sitae, Renvoi)",
            "Persons (Juridical Capacity, Capacity to Act, RA 6809, RA 11596)",
            "Family Relations — Marriage (FC Arts. 1-148: Void/Voidable Marriages, Foreign Divorce, Psychological Incapacity, Property Relations)",
            "Family Relations — Filiation and Adoption (FC Arts. 163-182, RA 11642 Domestic Adoption, RA 8043 Inter-Country, RA 11767 Foundlings)",
            "Family Relations — Support, Family Home, Parental Authority (FC Arts. 152-233)",
            "Civil Register (NCC Arts. 407-408, Rule 108, RA 9048 as amended, RA 11909, RA 11222)",
            "Property and Ownership (Immovable/Movable, Public Dominion, Co-ownership, Possession, Usufruct, Easements, Prescription)",
            "Land Titles and Deeds — Torrens System (PD 1529, Regalian Doctrine, Original Registration, Confirmation RA 11573, Certificate of Title, Assurance Fund, Reconstitution RA 26)",
            "Succession (NCC Arts. 774-1105: Testamentary, Intestate, Common Provisions, Distribution)",
            "Obligations (Classification, Extinguishment, Novation, Subrogation, Estoppel)",
            "Contracts (Essential Elements, Principles, Defective Contracts: Rescissible, Voidable, Unenforceable, Void)",
            "Special Contracts (Sale, Lease, Agency, Loan/Mutuum/Commodatum, Deposit, Guaranty/Suretyship, Real Estate Mortgage, Personal Property Security RA 11057)",
            "Quasi-contracts (Negotiorum Gestio, Solutio Indebiti)",
            "Torts and Quasi-delicts (Abuse of Right, Proximate Cause, Employer Liability, Medical Negligence, Nuisance)",
            "Damages (Actual, Moral, Nominal, Temperate, Liquidated, Exemplary)",
        ],
        "key_statutes": [
            "Civil Code of the Philippines (NCC)", "Family Code (EO 209)",
            "PD 1529 (Property Registration Decree)", "RA 11642 (Domestic Administrative Adoption Act)",
            "RA 11573 (Confirmation of Imperfect Title)", "RA 11057 (Personal Property Security Act)",
            "RA 6552 (Maceda Law — Realty Installment Buyer Protection)",
            "RA 11596 (Prohibition of Child Marriage)", "RA 11767 (Foundling Recognition and Protection Act)",
            "RA 26 (Reconstitution of Titles)", "RA 9048 as amended by RA 10172",
        ],
        "notable_cases": [
            "Tan-Andal v. Andal, G.R. No. 196359, May 11, 2021 (Psychological Incapacity — overruled Molina doctrine)",
            "Republic v. Molina, G.R. No. 108763, February 13, 1997 (old psychological incapacity standard — overruled by Tan-Andal)",
        ],
    },

    "criminal_law": {
        "title": "Criminal Law",
        "weight_pct": 10,
        "topics": [
            "Fundamental Principles (Construction, Pro Reo, Nullum Crimen, Mala In Se vs Mala Prohibita, Cardinal Principles, Constitutional Limitations)",
            "Felonies and Criminal Liability (Dolo/Culpa, Stages of Execution, Plurality of Crimes: Complex Crime, Composite Crime, Continuing Crime)",
            "Criminal Liability (Actus Reus, Mens Rea, Proximate Cause, Impossible Crime, Principals/Accomplices/Accessories, Conspiracy)",
            "Circumstances Affecting Liability (Justifying, Exempting, Mitigating, Aggravating, Alternative, Absolutory Causes, Instigation vs Entrapment)",
            "Penalties (Classification, Indeterminate Sentence Law, Probation, Good Conduct Time Allowance RA 10592)",
            "Extinction of Criminal Liability (Prescription, Pardon, Amnesty, Death)",
            "Civil Liability Ex Delicto",
            "Crimes against National Security (Terrorism RA 11479, Piracy, Genocide RA 9851)",
            "Crimes against Fundamental Laws (Torture RA 9745)",
            "Crimes against Public Interest (Cybercrime RA 10175: Computer Forgery, Fraud, Identity Theft, Cyber Libel)",
            "Dangerous Drugs (RA 9165 as amended by RA 10640)",
            "Crimes by Public Officers (Plunder RA 7080, Graft RA 3019, Unethical Conduct RA 6713)",
            "Crimes against Persons (Human Trafficking RA 9208, VAWC RA 9262, Child Abuse RA 7610, Rape RA 11648, Hazing RA 11053)",
            "Crimes against Property (Fencing PD 1612, Carnapping RA 10883/RA 11235, BP 22, Arson PD 1613)",
            "Crimes against Chastity and Honor (Photo/Video Voyeurism RA 9995, Cyber Libel RA 10175)",
            "Quasi-offenses — Morales v. People, G.R. No. 240337, January 2, 2022",
        ],
        "key_statutes": [
            "Revised Penal Code (RPC)", "RA 11479 (Anti-Terrorism Act)",
            "RA 9165 as amended by RA 10640 (Dangerous Drugs Act)", "RA 10175 (Cybercrime Prevention Act)",
            "RA 7080 as amended (Plunder Law)", "RA 3019 (Anti-Graft Law)",
            "RA 9208 as amended (Anti-Trafficking)", "RA 9262 (Anti-VAWC)",
            "RA 7610 as amended (Child Abuse)", "RA 11648 (Rape Law)",
            "RA 10591 (Firearms Law)", "RA 9344 as amended (JJWA)",
            "RA 10883 (Anti-Carnapping Act)", "PD 1612 (Anti-Fencing)", "BP Blg. 22 (Bouncing Checks Law)",
        ],
        "notable_cases": [
            "Morales v. People, G.R. No. 240337, January 2, 2022 (Quasi-offenses)",
        ],
    },

    "remedial_law": {
        "title": "Remedial Law, Legal and Judicial Ethics, With Practical Exercises",
        "weight_pct": 25,
        "topics": [
            # Civil Procedure
            "Jurisdiction (Subject Matter, Acquired, Philippine Courts — MTC, RTC, CA, SC, Sandiganbayan, CTA, Family Courts, RA 11576, Lupong Tagapamayapa)",
            "Civil Procedure — Rules of Court as amended by A.M. No. 19-10-20-SC (Classification of Actions, Pleadings, Summons, Motions, Dismissal, Default, Pre-trial, Modes of Discovery, Trial, Judgments)",
            "Post-judgment Remedies (New Trial, Reconsideration, Relief from Judgment Rule 38, Annulment of Judgment Rule 47, Appeal Rules 40-45 and 64)",
            "Execution of Judgments (Rule 39, Res Judicata, Enforcement of Foreign Judgments)",
            "Provisional Remedies (Attachment Rule 57, Preliminary Injunction Rule 58, Receivership, Replevin, Support Pendente Lite)",
            "Special Civil Actions (Interpleader, Declaratory Relief, Certiorari/Prohibition/Mandamus Rule 65, Quo Warranto, Expropriation, Foreclosure, Partition, Forcible Entry/Unlawful Detainer Rule 70, Contempt)",
            "Special Proceedings (Settlement of Estate: Extrajudicial Rule 74 / Intestate Rules 78-79 / Testate Rules 76-77; Guardianship; Habeas Corpus; Amparo; Habeas Data; Environmental Cases: Kalikasan, TEPO)",
            # Criminal Procedure
            "Criminal Procedure (Prosecution of Offenses Rule 110, Civil Action Rule 111, Preliminary Investigation Rule 112, Arrest Rule 113, Bail Rule 114, Arraignment Rule 116, Motion to Quash Rule 117, Trial Rule 119, Search and Seizure Rule 126, A.M. No. 17-11-03-SC Cybercrime Warrants)",
            # Evidence
            "Evidence (Admissibility, Judicial Notice, Judicial Admissions, Burden of Proof, Presumptions, Object Evidence, Documentary Evidence, Testimonial Evidence, Hearsay Rule, Opinion Rule, Electronic Evidence A.M. No. 01-7-01-SC, DNA Evidence A.M. No. 06-11-5-SC)",
            # Legal Ethics
            "Legal and Judicial Ethics — CPRA A.M. No. 22-09-01-SC (Practice of Law, Admission to Bar, Duties of Lawyers under Canons I-VI: Independence, Propriety, Fidelity, Competence, Equality; Discipline and Disbarment; Notarial Practice A.M. No. 02-8-13-SC)",
            "Judicial Ethics (NCJC A.M. No. 03-05-01-SC: Independence, Integrity, Impartiality, Propriety, Equality, Competence; Discipline of Judges Rule 140)",
            # Practical Exercises
            "Practical Exercises (Promissory Note, Demand Letter, Sale/Lease Contracts, Special Power of Attorney, Verification and Certification, Affidavits, Notarial Acts, Motions, Information)",
        ],
        "key_statutes": [
            "Rules of Court (as amended by A.M. No. 19-10-20-SC)",
            "CPRA — Code of Professional Responsibility and Accountability (A.M. No. 22-09-01-SC)",
            "New Code of Judicial Conduct (A.M. No. 03-05-01-SC)",
            "Rules on Electronic Evidence (A.M. No. 01-7-01-SC)",
            "Revised Rule on DNA Evidence (A.M. No. 06-11-5-SC)",
            "Rule on the Writ of Amparo (A.M. No. 07-9-12-SC)",
            "Rule on the Writ of Habeas Data (A.M. No. 08-1-16-SC)",
            "Rules of Procedure for Environmental Cases (A.M. No. 09-6-8-SC)",
            "Cybercrime Warrants (A.M. No. 17-11-03-SC)",
            "Body Camera Rules (A.M. No. 21-06-08)",
            "RA 11576 (Expanded MTC Jurisdiction)", "RA 7160 (LGC — Lupong Tagapamayapa)",
        ],
        "notable_cases": [
            "Neypes v. Court of Appeals, G.R. No. 141524, September 14, 2005 — Fresh Period Rule: a party has a fresh 15-day period to appeal from receipt of the order denying a motion for new trial/reconsideration, not from the original judgment",
            "Tijam v. Sibonghanoy, G.R. No. L-21450, April 15, 1968 — Estoppel by laches may bar a party from assailing jurisdiction after actively participating in proceedings for an unreasonable length of time",
            "Heirs of Maura So v. Obliosca, G.R. No. 147076, December 17, 2007 — Cascade-type questions on res judicata and litis pendentia",
            "Spouses Munoz v. Yabut, G.R. No. 142676, June 6, 2011 — Distinction between direct and collateral attack on title",
            "Stonehill v. Diokno, G.R. No. L-19550, June 19, 1967 — Exclusionary rule; illegally seized evidence inadmissible",
            "People v. Inting, G.R. No. 88919, July 25, 1990 — Probable cause in preliminary investigation; determination by prosecutor",
            "Dela Torre v. Comelec, G.R. No. 121592, July 5, 1996 — Probation bars candidacy; conviction not wiped out by probation",
            "Lorenzo Shipping Corp. v. Villarin, G.R. Nos. 175727 & 178713, March 6, 2019 (Provisional Deposit)",
            "Guerrero Estate Dev't Corp. v. Leviste & Guerrero Realty Corp., G.R. No. 253428, February 16, 2022",
            "Republic v. Caguioa, G.R. No. 168584, October 15, 2007 — Distinction between jurisdiction over subject matter and jurisdiction over the person",
            "Metrobank v. Perez, G.R. No. 181842, July 8, 2009 — Res judicata: bar by prior judgment vs. conclusiveness of judgment",
        ],
    },
}


def get_subject_for_topic(query: str) -> str | None:
    """Heuristic: return the subject key most likely covering this query."""
    q = query.lower()

    civil_signals = [
        "civil code", "family code", "marriage", "psychological incapacity", "void marriage",
        "succession", "contract", "obligation", "sale", "agency", "lease", "mortgage",
        "torrens", "land title", "regalian", "property", "easement", "usufruct",
        "co-ownership", "damages", "quasi-delict", "tort", "adoption", "filiation",
        "support", "parental authority",
    ]
    criminal_signals = [
        "revised penal code", "rpc", "felony", "crime", "penalty", "rape", "homicide",
        "murder", "robbery", "theft", "estafa", "plunder", "graft", "drug", "carnapping",
        "hazing", "trafficking", "vawc", "cybercrime", "cyber libel", "terrorism",
        "conspiracy", "accomplice", "accessories", "recidivism",
    ]
    labor_signals = [
        "labor code", "dismissal", "illegal dismissal", "reinstatement", "backwages",
        "nlrc", "labor arbiter", "collective bargaining", "strike", "unfair labor",
        "minimum wage", "overtime", "separation pay", "security of tenure", "ofw",
        "overseas worker", "sss", "gsis", "seafarer", "kasambahay", "maternity leave",
    ]
    political_signals = [
        "constitution", "due process", "equal protection", "bill of rights",
        "police power", "eminent domain", "taxation power", "executive", "legislative",
        "judicial review", "habeas corpus", "writ of amparo", "election law",
        "local government", "administrative law", "ombudsman", "sandiganbayan",
        "citizenship", "sovereignty", "public international", "treaty", "extradition",
        "comelec", "impeachment", "public officer",
    ]
    remedial_signals = [
        "rules of court", "jurisdiction", "certiorari", "mandamus", "prohibition",
        "civil procedure", "criminal procedure", "evidence", "hearsay", "bail",
        "preliminary investigation", "search warrant", "arrest", "pleading",
        "appeal", "execution of judgment", "res judicata", "legal ethics", "cpra",
        "disbarment", "notarial", "judicial ethics", "special proceedings", "habeas data",
        "kalikasan", "quo warranto rule 66",
        # landmark doctrines that should map to remedial law
        "neypes", "fresh period", "tijam", "sibonghanoy", "stonehill", "diokno",
        "estoppel by laches", "exclusionary rule", "fruit of the poisonous tree",
        "demurrer to evidence", "motion to dismiss", "forum shopping",
        "litis pendentia", "splitting cause of action", "cause of action",
        "substituted service", "service of summons", "summons",
        "modes of discovery", "deposition", "interrogatories",
        "writ of execution", "writ of possession",
    ]

    scores = {
        "civil_law": sum(1 for s in civil_signals if s in q),
        "criminal_law": sum(1 for s in criminal_signals if s in q),
        "labor_law": sum(1 for s in labor_signals if s in q),
        "political_law": sum(1 for s in political_signals if s in q),
        "remedial_law": sum(1 for s in remedial_signals if s in q),
    }

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else None


def build_bar_context_hint(subject_key: str | None) -> str:
    """
    Return a structured hint injected into the generation prompt for BAR 2026 questions.
    Includes notable landmark cases for the subject as supplementary reference.
    """
    if not subject_key or subject_key not in SUBJECTS:
        return (
            f"NOTE: This question may be relevant to the {BAR_EXAM_YEAR} Philippine Bar Examinations "
            f"(jurisprudence cutoff: {JURISPRUDENCE_CUTOFF}). "
            "Apply the applicable doctrine, cite the controlling case, and identify any superseding rules."
        )

    subj = SUBJECTS[subject_key]
    cases = subj.get("notable_cases", [])
    cases_block = ""
    if cases:
        cases_list = "\n".join(f"  - {c}" for c in cases)
        cases_block = (
            f"\n\nKEY LANDMARK CASES FOR THIS SUBJECT (use as supplementary reference "
            f"even if not in the retrieved sources above):\n{cases_list}"
        )

    return (
        f"NOTE: This is a {BAR_EXAM_YEAR} Bar Examinations question under "
        f"{subj['title']} ({subj['weight_pct']}% of the exam). "
        f"Only laws, rules, and jurisprudence up to {JURISPRUDENCE_CUTOFF} are examinable. "
        "Identify the applicable law/doctrine first, apply it to the facts, cite the controlling case, "
        f"and note any exceptions or superseding rules.{cases_block}"
    )

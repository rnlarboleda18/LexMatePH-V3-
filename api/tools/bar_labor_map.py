# bar_labor_map.py
# BAR 2026 — Labor Law and Social Legislation
# Coverage map: each entry = one syllabus sub-topic

LABOR_MAP = [
    # ─── I. General Principles ───────────────────────────────────────────────
    {
        "roman_num": "I",
        "sub_letter": "A",
        "heading": "Constitutional Basis: Labor Protection Mandate (Art. XIII, Secs. 1-3)",
        "provisions": [
            {"source": "const", "provision_id": "art-13-sec-1"},
            {"source": "const", "provision_id": "art-13-sec-2"},
            {"source": "const", "provision_id": "art-13-sec-3"},
            {
                "source": "ai",
                "note": (
                    "Article XIII of the 1987 Constitution mandates the State to afford full "
                    "protection to labor, local and overseas, organized and unorganized, and "
                    "promote full employment and equality of employment opportunities. Sec. 3 "
                    "guarantees workers' rights to self-organization, collective bargaining, "
                    "peaceful concerted activities including the right to strike, security of "
                    "tenure, humane conditions of work, and living wages."
                ),
            },
        ],
        "sort_order": 1,
    },
    {
        "roman_num": "I",
        "sub_letter": "B",
        "heading": "Labor Code Overview; Construction in Favor of Labor (PD 442)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_442_1974.html",
            },
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "4",
                "label": "Art. 4, Labor Code",
                "note": (
                    "Presidential Decree No. 442 (Labor Code of the Philippines), as amended, "
                    "is the primary statute governing employment relations, labor standards, "
                    "and labor relations. Art. 4 embodies the rule that all doubts in the "
                    "implementation and interpretation of the Labor Code, including its "
                    "implementing rules and regulations, shall be resolved in favor of labor. "
                    "This principle of liberal construction applies in both labor standards "
                    "and labor relations disputes."
                ),
            },
        ],
        "sort_order": 2,
    },
    {
        "roman_num": "I",
        "sub_letter": "C",
        "heading": "Employee vs. Independent Contractor; Four-Fold Test; Economic Reality Test",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "The four-fold test (selection and engagement, payment of wages, power of "
                    "dismissal, power of control) determines employer-employee relationship, "
                    "with the control test being the most determinative element. The economic "
                    "reality test supplements the four-fold test by examining whether the "
                    "worker is economically dependent on the alleged employer for his continued "
                    "employment in that line of business. An independent contractor carries on "
                    "an independent business, supplies his own tools, works for multiple "
                    "clients, and is free from employer control as to the means and methods of "
                    "accomplishing the result. Key SC cases: Insular Life v. NLRC, Tongko v. "
                    "Manufacturers Life, Atok Big Wedge v. Gison."
                ),
            },
        ],
        "sort_order": 3,
    },
    # ─── II. Labor Relations ─────────────────────────────────────────────────
    {
        "roman_num": "II",
        "sub_letter": "A",
        "heading": "Right to Self-Organization; Union Formation and Registration (PD 442 Book V; DO 40-03)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {"source": "const", "provision_id": "art-13-sec-3"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_442_1974.html",
            },
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "255",
                "label": "Art. 255, Labor Code",
                "note": (
                    "Book V of the Labor Code governs labor relations. Art. 243 (now Art. 255) "
                    "guarantees the right to self-organization for all persons employed in "
                    "commercial, industrial, and agricultural enterprises. DOLE Department "
                    "Order No. 40-03 (series 2003) and its amendments govern registration of "
                    "unions. A legitimate labor organization acquires legal personality upon "
                    "registration with the DOLE Bureau of Labor Relations (BLR). Minimum "
                    "membership: 20% of all employees in the bargaining unit for enterprise "
                    "unions. Independent unions register with the Regional Office; federations "
                    "and national unions register with the BLR."
                ),
            },
        ],
        "sort_order": 4,
    },
    {
        "roman_num": "II",
        "sub_letter": "B",
        "heading": "Collective Bargaining: Duty to Bargain, CBA, ULP by Employer and Union",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "261",
                "label": "Art. 261, Labor Code",
                "note": (
                    "Arts. 261-272 (renumbered) of the Labor Code impose a mutual duty on the "
                    "employer and the exclusive bargaining agent to bargain collectively in good "
                    "faith. The CBA is effective for five years; the representation aspect is "
                    "renegotiable every five years while economic provisions may be "
                    "renegotiated every three years. Surface bargaining and blue-sky bargaining "
                    "constitute bad-faith bargaining. The duty to bargain includes the duty to "
                    "execute a contract if agreement is reached. Violation of the duty to "
                    "bargain is an unfair labor practice (ULP)."
                ),
            },
        ],
        "sort_order": 5,
    },
    {
        "roman_num": "II",
        "sub_letter": "C",
        "heading": "Strikes and Lockouts: Requisites, Illegal Strikes, Liability (Arts. 264-279 LC)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "A valid strike requires: (1) it is conducted by a legitimate labor "
                    "organization; (2) based on a valid ground — ULP or collective bargaining "
                    "deadlock; (3) a notice of strike filed with NCMB at least 30 days before "
                    "intended date (15 days for ULP); (4) cooling-off period observed; (5) "
                    "strike vote approved by majority of union members in a secret ballot; "
                    "(6) strike vote report filed with NCMB at least 7 days before strike. "
                    "Illegal strikes: those violating the above requirements, those involving "
                    "prohibited activities (e.g., obstruction), or staged in industries "
                    "indispensable to national interest when the DOLE Secretary has assumed "
                    "jurisdiction. Union officers who knowingly participate in an illegal strike "
                    "may be terminated; ordinary members who commit illegal acts may likewise "
                    "be dismissed."
                ),
            },
        ],
        "sort_order": 6,
    },
    {
        "roman_num": "II",
        "sub_letter": "D",
        "heading": "Unfair Labor Practices: Enumeration and Remedies",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "ULP by employers (Art. 258, formerly Art. 248): interference with the "
                    "right to self-organization, yellow-dog contracts, contracting out work "
                    "to undermine union, company unionism, discrimination against union "
                    "members, refusal to bargain collectively, paid negotiation, violation of "
                    "duty to bargain, gross violation of CBA. ULP by labor organizations "
                    "(Art. 259, formerly Art. 249): restraint/coercion of employees, causing "
                    "discrimination by employer, featherbedding, refusal to bargain. ULP is "
                    "both civil (NLRC jurisdiction) and criminal (criminal liability of "
                    "officers) in nature. Prescriptive period: 1 year from accrual."
                ),
            },
        ],
        "sort_order": 7,
    },
    # ─── III. Employment Termination ─────────────────────────────────────────
    {
        "roman_num": "III",
        "sub_letter": "A",
        "heading": "Just Causes for Termination (Art. 297 LC): Serious Misconduct, Willful Disobedience, Gross Neglect, Fraud, Commission of Crime, Analogous Causes",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_442_1974.html",
            },
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "297",
                "label": "Art. 297, Labor Code",
                "note": (
                    "Art. 297 (formerly Art. 282) enumerates just causes attributable to the "
                    "employee: (a) serious misconduct or willful disobedience of lawful orders; "
                    "(b) gross and habitual neglect of duties; (c) fraud or willful breach of "
                    "trust; (d) commission of a crime or offense against the employer or his "
                    "immediate family; (e) other analogous causes. Dismissal for just cause "
                    "entitles the employee to no separation pay, but backwages may be awarded "
                    "if procedural due process was not observed. The misconduct must be "
                    "work-related and of such serious nature as to render continued employment "
                    "impossible."
                ),
            },
        ],
        "sort_order": 8,
    },
    {
        "roman_num": "III",
        "sub_letter": "B",
        "heading": "Authorized Causes (Arts. 298-299 LC): Retrenchment, Redundancy, Closure, Disease",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "298",
                "label": "Art. 298, Labor Code",
                "note": (
                    "Art. 298 (formerly Art. 283) authorizes termination for installation of "
                    "labor-saving devices, redundancy, retrenchment to prevent losses, closure "
                    "or cessation of operations, and disease where continued employment is "
                    "prohibited by law or prejudicial to the employee's health or co-workers'. "
                    "Separation pay: one month pay or one month per year of service, whichever "
                    "is higher, for redundancy; one-half month per year for retrenchment, "
                    "closure not due to financial losses, and disease. One-month notice to "
                    "DOLE and employee is mandatory. Art. 299 (formerly Art. 284) covers "
                    "disease as authorized cause."
                ),
            },
        ],
        "sort_order": 9,
    },
    {
        "roman_num": "III",
        "sub_letter": "C",
        "heading": "Procedural Due Process: Twin-Notice Rule; Opportunity to Be Heard",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "Procedural due process in termination for just cause requires: (1) first "
                    "written notice specifying the ground and directing the employee to explain "
                    "within a reasonable period (at least 5 calendar days under DO 147-15); "
                    "(2) an opportunity to be heard — a hearing or conference; (3) second "
                    "written notice informing the employee of the decision to dismiss. Violation "
                    "of procedural due process does not invalidate the dismissal but entitles "
                    "the employee to nominal damages (Agabon doctrine): PHP 30,000 for just "
                    "cause; PHP 50,000 for authorized cause (Jaka Food Processing v. Pacot). "
                    "For authorized causes, one written notice to DOLE and one to the employee "
                    "at least 30 days before effectivity suffices."
                ),
            },
        ],
        "sort_order": 10,
    },
    {
        "roman_num": "III",
        "sub_letter": "D",
        "heading": "Illegal Dismissal: Reinstatement, Backwages, Separation Pay in Lieu",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "294",
                "label": "Art. 294, Labor Code",
                "note": (
                    "An illegally dismissed employee is entitled to: (1) reinstatement without "
                    "loss of seniority rights and other privileges; (2) full backwages, "
                    "inclusive of allowances and other benefits, computed from the time of "
                    "dismissal to actual reinstatement (Art. 294, formerly Art. 279). "
                    "Reinstatement is immediately executory even pending appeal (Art. 229). "
                    "If reinstatement is no longer feasible due to strained relations, "
                    "separation pay equivalent to one month per year of service is awarded in "
                    "lieu thereof (Strained Relations Doctrine — Globe-Mackay). Backwages are "
                    "not reduced by earnings elsewhere (Mercury Drug rule post-RA 6715)."
                ),
            },
        ],
        "sort_order": 11,
    },
    {
        "roman_num": "III",
        "sub_letter": "E",
        "heading": "Constructive Dismissal",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "Constructive dismissal exists when an act of clear discrimination, "
                    "insensibility, or disdain by an employer becomes so unbearable as to "
                    "leave an employee with no choice but to forego continued employment. "
                    "Examples: demotion in rank or diminution in pay without valid reason, "
                    "transfer to a remote or inconvenient location without legitimate business "
                    "purpose, harassment or hostile work environment. The burden shifts to the "
                    "employer to prove the transfer/demotion was not motivated by ill will. "
                    "Relief is the same as illegal dismissal: reinstatement or separation pay "
                    "plus full backwages."
                ),
            },
        ],
        "sort_order": 12,
    },
    # ─── IV. Wages and Working Conditions ────────────────────────────────────
    {
        "roman_num": "IV",
        "sub_letter": "A",
        "heading": "Minimum Wage: Regional Tripartite Wages and Productivity Boards (RA 6727)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-6727"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1989/ra_6727_1989.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 6727 (Wage Rationalization Act) created the Regional Tripartite Wages "
                    "and Productivity Boards (RTWPBs) in each region empowered to determine "
                    "and fix minimum wage rates applicable in their respective regions, "
                    "provinces, or industries. Factors considered: demand for living wages, "
                    "wage adjustment vis-à-vis Consumer Price Index, cost of living and "
                    "production costs, needs of workers and their families, and employer's "
                    "capacity to pay. Wage orders issued by RTWPBs may be appealed to the "
                    "National Wages and Productivity Commission (NWPC) within 10 days of "
                    "publication. Non-diminution: wage increases under wage orders cannot be "
                    "credited against future increases unless agreed upon."
                ),
            },
        ],
        "sort_order": 13,
    },
    {
        "roman_num": "IV",
        "sub_letter": "B",
        "heading": "Overtime, Holiday Pay, Night Shift Differential, Service Incentive Leave (Arts. 82-95 LC)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_442_1974.html",
            },
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "82",
                "label": "Art. 82, Labor Code",
                "note": (
                    "Arts. 82-95 of the Labor Code (Book III, Title I) govern hours of work "
                    "and rest periods. Normal hours: 8 hours/day. Overtime: plus 25% of "
                    "regular hourly rate on ordinary days; plus 30% on rest days or special "
                    "days. Holiday pay: 100% on regular holidays (12 regular holidays under "
                    "RA 9492); if worked, 200% for the first 8 hours. Special non-working "
                    "holidays: 130% if worked. Night shift differential: 10% additional for "
                    "work between 10:00 PM and 6:00 AM. Service incentive leave: 5 days per "
                    "year for employees who have rendered at least one year of service, "
                    "convertible to cash if unused. Exemptions: managerial employees, field "
                    "personnel, domestic helpers, those paid by results."
                ),
            },
        ],
        "sort_order": 14,
    },
    {
        "roman_num": "IV",
        "sub_letter": "C",
        "heading": "13th Month Pay (PD 851)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-851"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/presdecs/pd1975/pd_851_1975.html",
            },
            {
                "source": "ai",
                "note": (
                    "PD 851 requires all employers in the private sector to pay their rank-and-"
                    "file employees a 13th month pay not later than December 24 of each year. "
                    "Minimum: 1/12 of the total basic salary earned within a calendar year. "
                    "Employees who have worked for at least one month in a calendar year are "
                    "entitled. Managerial employees are excluded. The 13th month pay is "
                    "exempt from income tax up to PHP 90,000 (as amended by TRAIN Law, RA "
                    "10963). Employers may pay in two tranches: half by end of June and the "
                    "remaining half by December 24."
                ),
            },
        ],
        "sort_order": 15,
    },
    {
        "roman_num": "IV",
        "sub_letter": "D",
        "heading": "Non-Diminution of Benefits",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "100",
                "label": "Art. 100, Labor Code",
                "note": (
                    "Art. 100 of the Labor Code prohibits the elimination or diminution of "
                    "existing benefits already enjoyed by employees. The non-diminution rule "
                    "applies to benefits that have ripened into company practice — i.e., given "
                    "over a long period of time, consistently and deliberately, such that "
                    "employees have come to rely on it as part of their compensation. A "
                    "mistake in giving a benefit does not necessarily give rise to a "
                    "practice. Benefits may be reduced if done with the express consent of "
                    "the employees through a valid CBA."
                ),
            },
        ],
        "sort_order": 16,
    },
    # ─── V. Recruitment and Placement ────────────────────────────────────────
    {
        "roman_num": "V",
        "sub_letter": "A",
        "heading": "Recruitment Agencies; Illegal Recruitment (RA 8042 as amended by RA 10022)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-8042"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1995/ra_8042_1995.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 8042 (Migrant Workers and Overseas Filipinos Act of 1995), as amended "
                    "by RA 10022 (2010), defines and penalizes illegal recruitment. Illegal "
                    "recruitment: any act of recruitment undertaken by non-licensees or "
                    "non-holders of authority, or any prohibited act enumerated under Art. 34 "
                    "of the Labor Code even if done by licensed agencies. It is economic "
                    "sabotage when committed by a syndicate (3 or more persons) or in large "
                    "scale (3 or more victims). Penalty: life imprisonment and fine of not "
                    "less than PHP 2M for economic sabotage. Private recruitment agencies must "
                    "be licensed by the DOLE/POEA. Solidary liability of local agency and "
                    "foreign principal."
                ),
            },
        ],
        "sort_order": 17,
    },
    {
        "roman_num": "V",
        "sub_letter": "B",
        "heading": "Overseas Filipino Workers: POEA, OWWA, OFW Rights",
        "provisions": [
            {"source": "statute", "provision_id": "ra-8042"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1995/ra_8042_1995.html",
            },
            {
                "source": "ai",
                "note": (
                    "The Philippine Overseas Employment Administration (POEA) regulates "
                    "overseas deployment; the Overseas Workers Welfare Administration (OWWA) "
                    "handles welfare and benefits. OFW rights: right to a written contract "
                    "translated into a language understood by the worker; right to a free "
                    "placement (no fees from worker); right to repatriation at employer's "
                    "expense; right to receive salary not less than the POEA-approved "
                    "standard employment contract rate; right to access OWWA benefits "
                    "(repatriation assistance, skills training, livelihood programs). "
                    "Undocumented workers are still entitled to rights and benefits under "
                    "Philippine law. RA 10022 strengthened deployment ban to countries not "
                    "meeting minimum labor standards."
                ),
            },
        ],
        "sort_order": 18,
    },
    {
        "roman_num": "V",
        "sub_letter": "C",
        "heading": "Labor-Only Contracting vs. Permissible Contracting (DO 174-17)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "DOLE Department Order No. 174-17 (2017) governs contracting and "
                    "subcontracting arrangements. Labor-only contracting (LOC) is prohibited: "
                    "it exists when the contractor (a) does not have substantial capital or "
                    "investment; and (b) the workers recruited perform activities directly "
                    "related to the principal's main business. In LOC, the principal is deemed "
                    "the employer. Permissible job contracting requires: contractor must be "
                    "registered with DOLE; must have substantial capital (PHP 5M minimum); "
                    "service agreement must specify benefits to workers; contractor must "
                    "exercise control over the means and methods of work. Prohibited "
                    "contracting arrangements include 5/6 scheme, cabo, and clandestine LOC."
                ),
            },
        ],
        "sort_order": 19,
    },
    # ─── VI. Special Workers ─────────────────────────────────────────────────
    {
        "roman_num": "VI",
        "sub_letter": "A",
        "heading": "Women Workers: Maternity Leave (RA 11210 — 105-Day Expanded Maternity Leave); Solo Parents (RA 8972)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-11210"},
            {"source": "statute", "provision_id": "ra-8972"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2019/ra_11210_2019.html",
            },
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2000/ra_8972_2000.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 11210 (Expanded Maternity Leave Law, 2019) grants 105 days paid "
                    "maternity leave for live birth (normal or CS), regardless of civil status "
                    "or legitimacy of child; 60 days for miscarriage/emergency termination. "
                    "Solo parents under RA 8972 get additional 15 days. The benefit is "
                    "chargeable to SSS and employer contributions. Extended 30 days optional "
                    "leave without pay may be availed. Leave may be transferred to the "
                    "qualified father/alternate caregiver for 7 days. RA 8972 (Solo Parents' "
                    "Welfare Act) grants solo parents: flexible work schedule, additional "
                    "parental leave of 7 days per year, educational assistance, housing "
                    "priority, and medical assistance, upon presentation of a Solo Parent ID."
                ),
            },
        ],
        "sort_order": 20,
    },
    {
        "roman_num": "VI",
        "sub_letter": "B",
        "heading": "Child Labor: RA 9231; Hazardous Work Prohibition",
        "provisions": [
            {"source": "statute", "provision_id": "ra-9231"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2003/ra_9231_2003.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 9231 (Special Protection of Children Against Abuse, Exploitation and "
                    "Discrimination Act) amends RA 7610 and prohibits the employment of "
                    "children below 15 years old unless the child works under the sole "
                    "responsibility of parents/guardians, the work does not interfere with "
                    "schooling, and the environment is not hazardous. Children 15-17 may be "
                    "employed but not in hazardous or deleterious undertakings. Employers "
                    "must secure a work permit from DOLE. Hazardous work: work in dangerous "
                    "machinery, exposure to toxic chemicals, underground or underwater work, "
                    "work that involves carrying heavy loads, work in bars or similar "
                    "establishments serving alcoholic beverages. Penalties: imprisonment "
                    "and/or fine."
                ),
            },
        ],
        "sort_order": 21,
    },
    {
        "roman_num": "VI",
        "sub_letter": "C",
        "heading": "Persons with Disabilities: RA 7277 (Magna Carta for Disabled Persons)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-7277"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1992/ra_7277_1992.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 7277 (Magna Carta for Disabled Persons, 1992), as amended by RA 9442 "
                    "and RA 10524, prohibits discrimination against qualified individuals with "
                    "disability in all aspects of employment. Employers are encouraged to "
                    "hire PWDs through a 25% additional deduction from gross income for wages "
                    "paid to PWD employees. Private entities employing PWDs are entitled to "
                    "additional deduction from taxable income equivalent to 25% of the total "
                    "amount paid as salaries and wages. Public and private establishments "
                    "must provide reasonable accommodations. At least 1% of total employment "
                    "in government agencies shall be reserved for PWDs (RA 10524 amendment). "
                    "PWDs are entitled to a 20% discount on specified goods and services."
                ),
            },
        ],
        "sort_order": 22,
    },
    {
        "roman_num": "VI",
        "sub_letter": "D",
        "heading": "Kasambahay: RA 10361 (Batas Kasambahay)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-10361"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2012/ra_10361_2012.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 10361 (Domestic Workers Act / Batas Kasambahay, 2013) regulates "
                    "employment of domestic workers (kasambahay). Minimum wage: PHP 5,000/month "
                    "in NCR; PHP 3,500 in chartered cities and first-class municipalities; "
                    "PHP 3,000 elsewhere. Mandatory benefits: SSS, PhilHealth, Pag-IBIG "
                    "contributions paid by employer; 5 days service incentive leave; rest day "
                    "of at least 24 consecutive hours per week; 13th month pay. Written "
                    "employment contract required. Pre-employment medical certificate required "
                    "at employer's expense. Prohibition on deposits and bonds. Termination: "
                    "just and authorized causes apply with proportionate separation pay. "
                    "Kasambahay may terminate within 5 days without penalty during first 15 "
                    "days of employment."
                ),
            },
        ],
        "sort_order": 23,
    },
    {
        "roman_num": "VI",
        "sub_letter": "E",
        "heading": "Night Workers, Househelpers, Homeworkers (Arts. 149-155 LC and related provisions)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "Arts. 154-161 of the Labor Code cover night workers in establishments "
                    "allowed to operate at night; they are entitled to: alternative working "
                    "arrangements, health assessments, first aid facilities, and transfer "
                    "to day work if health is adversely affected. Homeworkers are governed "
                    "by Arts. 153-155 and implementing rules: they must be registered with "
                    "DOLE; payment is on a piece-rate basis; the employer/contractor is "
                    "responsible for safety and health conditions. Househelpers (domestic "
                    "workers) were previously governed by Arts. 141-152 but are now primarily "
                    "covered by RA 10361 (Batas Kasambahay) which repealed the relevant Labor "
                    "Code provisions. Children below 15 may not be employed as househelpers."
                ),
            },
        ],
        "sort_order": 24,
    },
    # ─── VII. Labor Dispute Resolution ───────────────────────────────────────
    {
        "roman_num": "VII",
        "sub_letter": "A",
        "heading": "NLRC: Jurisdiction, Appeals, Finality of Awards",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "229",
                "label": "Art. 229, Labor Code",
                "note": (
                    "The National Labor Relations Commission (NLRC) is a quasi-judicial body "
                    "that exercises appellate jurisdiction over decisions of Labor Arbiters "
                    "(Art. 229, formerly Art. 223). Appeals to NLRC must be filed within 10 "
                    "calendar days from receipt of the Labor Arbiter's decision. A cash bond "
                    "or surety bond in the amount of the monetary award is required for "
                    "appeals involving monetary awards. NLRC decisions become final and "
                    "executory 10 calendar days from receipt if not appealed. Further review: "
                    "Rule 65 certiorari to the Court of Appeals (St. Martin Funeral Homes "
                    "doctrine), then to the Supreme Court. NLRC has original jurisdiction over "
                    "inter-union and intra-union disputes through its Med-Arbitration units."
                ),
            },
        ],
        "sort_order": 25,
    },
    {
        "roman_num": "VII",
        "sub_letter": "B",
        "heading": "Labor Arbiter: Jurisdiction, Money Claims, Illegal Dismissal",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "224",
                "label": "Art. 224, Labor Code",
                "note": (
                    "Labor Arbiters have original and exclusive jurisdiction (Art. 224, "
                    "formerly Art. 217) over: unfair labor practice cases; termination "
                    "disputes; money claims exceeding PHP 5,000 per claim arising from "
                    "employer-employee relations; claims for actual, moral, exemplary, and "
                    "other forms of damages arising from employer-employee relations; cases "
                    "arising from RA 6727 (wage rationalization). Claims not exceeding PHP "
                    "5,000 with no reinstatement claim are within DOLE Regional Director's "
                    "jurisdiction under Art. 129. Labor Arbiters may award reinstatement "
                    "pending appeal (immediately executory). OFW illegal dismissal: Labor "
                    "Arbiter jurisdiction; monetary award limited to the unexpired portion "
                    "of the contract or 3 months salary per year, whichever is less "
                    "(RA 8042, as clarified by Sameer Overseas v. Cabiles)."
                ),
            },
        ],
        "sort_order": 26,
    },
    {
        "roman_num": "VII",
        "sub_letter": "C",
        "heading": "Voluntary Arbitration: Grievance Machinery, CBA Arbitration",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "274",
                "label": "Art. 274, Labor Code",
                "note": (
                    "Art. 274 (formerly Art. 261) requires all CBAs to include a grievance "
                    "machinery for the adjustment and resolution of grievances arising from "
                    "the interpretation or implementation of the CBA and company personnel "
                    "policies. Unresolved grievances must be referred to voluntary arbitration. "
                    "Voluntary Arbitrators (VAs) have exclusive and original jurisdiction "
                    "over unresolved grievances and wage distortion disputes in organized "
                    "establishments. VA decisions are final, executory, and unappealable "
                    "except on grounds of grave abuse of discretion via Rule 65 to the Court "
                    "of Appeals. NCMB maintains a list of accredited VAs. Parties must share "
                    "costs of VA unless CBA provides otherwise."
                ),
            },
        ],
        "sort_order": 27,
    },
    {
        "roman_num": "VII",
        "sub_letter": "D",
        "heading": "DOLE Secretary: Assumption of Jurisdiction (Art. 278 LC)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "db",
                "statute_id": "LABOR",
                "provision_id": "278",
                "label": "Art. 278, Labor Code",
                "note": (
                    "Art. 278 (formerly Art. 263(g)) empowers the DOLE Secretary to assume "
                    "jurisdiction over a labor dispute in an industry indispensable to the "
                    "national interest, or certify it to the NLRC for compulsory arbitration. "
                    "Upon assumption or certification, strikes and lockouts are enjoined and "
                    "striking or locked-out employees must immediately return to work. Failure "
                    "to comply is a ground for dismissal or loss of employment status. The "
                    "Secretary's assumption power is self-executory; no prior hearing is "
                    "required. The Secretary may also call the parties to conciliation "
                    "conferences and issue rulings binding on the parties. Violation of "
                    "assumption orders constitutes contempt and is punishable accordingly."
                ),
            },
        ],
        "sort_order": 28,
    },
    {
        "roman_num": "VII",
        "sub_letter": "E",
        "heading": "Small Money Claims; Single Entry Approach (SEnA)",
        "provisions": [
            {"source": "statute", "provision_id": "pd-442"},
            {
                "source": "ai",
                "note": (
                    "The Single Entry Approach (SEnA) under DO 107-10 and RA 10396 (2013) "
                    "provides a 30-day mandatory conciliation-mediation period before any "
                    "labor case is filed before the NLRC, DOLE offices, NCMB, or POEA. The "
                    "SEnA Desk Officer (SEADO) facilitates settlement. If no settlement is "
                    "reached, a referral document is issued enabling the complainant to file "
                    "the case formally. The 30-day period is not extendible except by written "
                    "agreement of the parties. Claims settled through SEnA are final and "
                    "binding. Money claims not exceeding PHP 5,000 without reinstatement: "
                    "DOLE Regional Director has jurisdiction; decision appealable to DOLE "
                    "Secretary within 5 days."
                ),
            },
        ],
        "sort_order": 29,
    },
    # ─── VIII. Social Security System ────────────────────────────────────────
    {
        "roman_num": "VIII",
        "sub_letter": "A",
        "heading": "SSS Coverage, Contributions, and Benefits (RA 8282 as amended by RA 11199)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-8282"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1997/ra_8282_1997.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 8282 (Social Security Act of 1997), as amended by RA 11199 (Social "
                    "Security Act of 2018), covers all private-sector employees, self-employed "
                    "persons, OFWs, and household workers. Contributions are shared between "
                    "employer (larger share) and employee, based on monthly salary credit. "
                    "RA 11199 increased contribution rates progressively and raised the "
                    "maximum monthly salary credit. SSS benefits: sickness (90% of average "
                    "daily salary credit for up to 120 days/year); maternity (coordinated "
                    "with RA 11210); disability (monthly pension or lump sum); retirement "
                    "(monthly pension or lump sum at age 60 with 120 monthly contributions, "
                    "or age 65); death/funeral (survivor's pension or lump sum; PHP 20,000 "
                    "minimum funeral benefit). Employer's failure to remit: solidary liability "
                    "of responsible officers."
                ),
            },
        ],
        "sort_order": 30,
    },
    {
        "roman_num": "VIII",
        "sub_letter": "B",
        "heading": "SSS Benefit Details: Sickness, Maternity, Disability, Retirement, Death/Funeral",
        "provisions": [
            {"source": "statute", "provision_id": "ra-8282"},
            {
                "source": "ai",
                "note": (
                    "Sickness benefit: member must have at least 3 monthly contributions in "
                    "the 12-month period immediately before semester of sickness; confined for "
                    "at least 4 days. Maternity: now governed primarily by RA 11210; SSS pays "
                    "100% of average daily salary credit for covered days. Disability: total "
                    "permanent disability entitles member to monthly pension if with at least "
                    "36 monthly contributions; otherwise lump sum. Retirement: age 60 "
                    "optional, age 65 compulsory, minimum 120 monthly contributions for "
                    "pension; otherwise lump sum. Death benefit: primary beneficiaries receive "
                    "monthly pension or lump sum; secondary beneficiaries if no primary. "
                    "Funeral grant: fixed amount (currently PHP 20,000 minimum) paid to "
                    "whoever defrayed funeral expenses."
                ),
            },
        ],
        "sort_order": 31,
    },
    # ─── IX. GSIS ─────────────────────────────────────────────────────────────
    {
        "roman_num": "IX",
        "sub_letter": "A",
        "heading": "GSIS Act (RA 8291): Coverage, Contributions, Benefits",
        "provisions": [
            {"source": "statute", "provision_id": "ra-8291"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1997/ra_8291_1997.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 8291 (Government Service Insurance System Act of 1997) covers all "
                    "government employees receiving fixed monthly compensation except "
                    "contractual, casual, and emergency employees, and uniformed personnel "
                    "covered by separate laws. Employee contribution: 9% of monthly "
                    "compensation; government share: 12%. Benefits: life insurance, retirement, "
                    "separation, disability, survivorship, and funeral. Enhanced Life Policy "
                    "(ELP) is the basic policy for compulsory coverage. GSIS also administers "
                    "the Employees' Compensation Program (ECP) for government employees."
                ),
            },
        ],
        "sort_order": 32,
    },
    {
        "roman_num": "IX",
        "sub_letter": "B",
        "heading": "GSIS Separation Benefits, Retirement, Life Insurance",
        "provisions": [
            {"source": "statute", "provision_id": "ra-8291"},
            {
                "source": "ai",
                "note": (
                    "Retirement under RA 8291: two modes — (1) 60 years old with at least 15 "
                    "years of service; or (2) 65 years old regardless of length of service. "
                    "Retirement benefit: 5-year lump sum and monthly pension thereafter, or "
                    "cash payment equivalent to 18x monthly pension plus old-age pension for "
                    "life. Separation benefit: for those with at least 3 but less than 15 "
                    "years of service who separate from service before age 60 — cash payment "
                    "of 100% of AMC per year of service. Life insurance: face value is "
                    "equivalent to member's most recent annual compensation. Survivorship "
                    "pension: 50% of deceased member's pension to the surviving spouse; "
                    "children entitled to additional 10% up to a maximum of 4 children."
                ),
            },
        ],
        "sort_order": 33,
    },
    # ─── X. PhilHealth ───────────────────────────────────────────────────────
    {
        "roman_num": "X",
        "sub_letter": "A",
        "heading": "PhilHealth (RA 7875 as amended); Universal Health Care Act (RA 11223)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-7875"},
            {"source": "statute", "provision_id": "ra-11223"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1995/ra_7875_1995.html",
            },
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2019/ra_11223_2019.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 7875 (National Health Insurance Act of 1995) established PhilHealth "
                    "to provide health insurance coverage and ensure affordable health care "
                    "services. RA 11223 (Universal Health Care Act, 2019) automatically "
                    "enrolls all Filipinos in PhilHealth: those in the formal economy as "
                    "direct contributors; indigents, senior citizens, and PWDs as "
                    "indirect/subsidized members. Mandatory PhilHealth contributions: "
                    "progressively increasing towards 5% of monthly basic salary (shared "
                    "equally). Benefit packages include inpatient room and board, medicines, "
                    "laboratory and diagnostic procedures, professional fees, and outpatient "
                    "benefits under Z-Benefit and case-rate packages. No balance billing "
                    "policy for indigent and sponsored members in government hospitals."
                ),
            },
        ],
        "sort_order": 34,
    },
    {
        "roman_num": "X",
        "sub_letter": "B",
        "heading": "PhilHealth Benefit Packages and Mandatory Contributions",
        "provisions": [
            {"source": "statute", "provision_id": "ra-7875"},
            {"source": "statute", "provision_id": "ra-11223"},
            {
                "source": "ai",
                "note": (
                    "PhilHealth benefit packages: All Case Rates (ACR) system sets fixed "
                    "payments for specific medical cases; Z-Benefits cover catastrophic "
                    "illnesses (cancer, renal failure, etc.); Maternity Care Package; Newborn "
                    "Care Package; Primary Care Benefit (PCB); TB-DOTS; Animal Bite Treatment. "
                    "Under RA 11223, outpatient services in primary care facilities and "
                    "epidemiologically critical conditions are covered. Contributions: shared "
                    "equally by employer and employee, based on monthly basic salary, "
                    "transitioning to 5% by 2025. Self-employed and OFW members pay both "
                    "shares. Non-remittance by employer: criminal liability and civil "
                    "surcharges."
                ),
            },
        ],
        "sort_order": 35,
    },
    # ─── XI. Pag-IBIG ────────────────────────────────────────────────────────
    {
        "roman_num": "XI",
        "sub_letter": "A",
        "heading": "Pag-IBIG Fund / Home Development Mutual Fund (RA 9679): Membership, Contributions, Housing Loans",
        "provisions": [
            {"source": "statute", "provision_id": "ra-9679"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2009/ra_9679_2009.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 9679 (Home Development Mutual Fund Law of 2009) mandates membership "
                    "of all employees covered by SSS and GSIS, as well as self-employed and "
                    "voluntary members. Monthly contribution: 1-2% of monthly compensation "
                    "by employee, matched equally by employer (capped at PHP 100/month "
                    "employee and employer share under standard scheme; higher contributions "
                    "for modified MP2 savings). Housing Loan: members may avail of "
                    "multi-purpose loans and housing loans after 24 monthly contributions. "
                    "Maximum housing loan: PHP 6M (as updated). Short-term loan (STL/MPL): "
                    "available after 24 monthly contributions. HDMF shares are returnable "
                    "upon retirement, disability, separation, or migration. Dividends are "
                    "tax-free."
                ),
            },
        ],
        "sort_order": 36,
    },
    # ─── XII. ECC and State Insurance Fund ───────────────────────────────────
    {
        "roman_num": "XII",
        "sub_letter": "A",
        "heading": "Employees' Compensation Commission (ECC) and State Insurance Fund (PD 626): Compensable Injuries/Diseases; Disability Grades",
        "provisions": [
            {"source": "statute", "provision_id": "pd-626"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/presdecs/pd1974/pd_626_1974.html",
            },
            {
                "source": "ai",
                "note": (
                    "PD 626 (Employees' Compensation and State Insurance Fund) governs the "
                    "State Insurance Fund administered by the ECC, SSS (for private sector), "
                    "and GSIS (for government sector). A work-related injury or disease is "
                    "compensable if: arising out of and in the course of employment. The "
                    "three-point theory: injury occurs at workplace, during working hours, "
                    "and while performing official functions. Listed occupational diseases "
                    "under Annex 'A' of PD 626 rules are disputably presumed compensable. "
                    "Non-listed diseases must be proven work-related by substantial evidence. "
                    "Disability schedule: Schedules of Disability Grades (1-14) determine "
                    "compensation amounts. Permanent total disability: maximum income benefit "
                    "for life. Benefits: medical services, rehabilitation, income benefit. "
                    "ECC benefits are distinct from and additional to SSS/GSIS benefits."
                ),
            },
        ],
        "sort_order": 37,
    },
    {
        "roman_num": "XII",
        "sub_letter": "B",
        "heading": "Relationship of ECC with SSS and GSIS",
        "provisions": [
            {"source": "statute", "provision_id": "pd-626"},
            {"source": "statute", "provision_id": "ra-8282"},
            {"source": "statute", "provision_id": "ra-8291"},
            {
                "source": "ai",
                "note": (
                    "ECC benefits are separate from and cumulative with SSS and GSIS benefits. "
                    "A worker who suffers a work-related injury may simultaneously claim: "
                    "(1) ECC disability/sickness benefit from the State Insurance Fund; "
                    "(2) SSS sickness/disability benefit for private-sector workers; or "
                    "(3) GSIS disability benefit for government workers. The State Insurance "
                    "Fund is funded entirely by employer contributions (no employee "
                    "contribution for ECC purposes); this distinguishes it from SSS and GSIS "
                    "which are contributory schemes. Claims are filed with SSS/GSIS which acts "
                    "as the administering agency; appeals go to the ECC, then to the Court of "
                    "Appeals via Rule 43."
                ),
            },
        ],
        "sort_order": 38,
    },
    # ─── XIII. Anti-Sexual Harassment / Safe Spaces ──────────────────────────
    {
        "roman_num": "XIII",
        "sub_letter": "A",
        "heading": "Anti-Sexual Harassment Act (RA 7877)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-7877"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra1995/ra_7877_1995.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 7877 (Anti-Sexual Harassment Act of 1995) penalizes sexual harassment "
                    "committed in a work-related or employment environment by a person having "
                    "authority, influence, or moral ascendancy over the victim. Elements: "
                    "(1) authority/influence/moral ascendancy by the offender; (2) demand, "
                    "request, or requirement of sexual favors; (3) refusal results in "
                    "discrimination or deprivation affecting employment, education, or training. "
                    "Employers must: prevent SH, establish a committee on decorum and "
                    "investigation (CODI), disseminate rules and regulations, create a "
                    "mechanism for lodging complaints. Employer is solidarily liable if SH "
                    "was committed by a supervisor and the employer failed to prevent it "
                    "despite knowledge. Criminal penalty: 1-6 months imprisonment and/or "
                    "PHP 10,000-20,000 fine."
                ),
            },
        ],
        "sort_order": 39,
    },
    {
        "roman_num": "XIII",
        "sub_letter": "B",
        "heading": "Safe Spaces Act (RA 11313)",
        "provisions": [
            {"source": "statute", "provision_id": "ra-11313"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2019/ra_11313_2019.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 11313 (Safe Spaces Act / Bawal Bastos Law, 2019) expands the coverage "
                    "of anti-sexual harassment law beyond authority relationships to include "
                    "peer-to-peer gender-based sexual harassment in streets, public spaces, "
                    "online spaces, and workplaces. Workplace coverage: gender-based sexual "
                    "harassment between co-workers regardless of seniority, employees against "
                    "superiors, and by third parties (clients, customers). Employers must: "
                    "disseminate the law, create an independent mechanism (separate from RA "
                    "7877 CODI), investigate complaints within 10 days. Acts penalized: "
                    "catcalling, wolf-whistling, unsolicited sexual comments, unwanted "
                    "invitations, persistent telling of sexual jokes, unwanted touching. "
                    "Penalties range from community service and fines to imprisonment "
                    "depending on gravity and repeat offenses."
                ),
            },
        ],
        "sort_order": 40,
    },
    # ─── XIV. Data Privacy in the Workplace ──────────────────────────────────
    {
        "roman_num": "XIV",
        "sub_letter": "A",
        "heading": "Data Privacy Act in the Workplace (RA 10173): Employee Personal Information, CCTV, Monitoring",
        "provisions": [
            {"source": "statute", "provision_id": "ra-10173"},
            {
                "source": "lawphil",
                "url": "https://lawphil.net/statutes/repacts/ra2012/ra_10173_2012.html",
            },
            {
                "source": "ai",
                "note": (
                    "RA 10173 (Data Privacy Act of 2012) applies to the processing of personal "
                    "information of employees by their employers. Key principles: (1) "
                    "Transparency — employees must be informed of the collection and use of "
                    "their personal data; (2) Legitimate Purpose — collection must be "
                    "compatible with a declared purpose; (3) Proportionality — data collected "
                    "must be adequate, relevant, and not excessive. Employment exception: "
                    "processing necessary for the employment relationship does not require "
                    "employee consent but employer must still comply with DPA principles. "
                    "CCTV/workplace monitoring: permissible if employees are notified, "
                    "monitoring is for legitimate business purposes (security, productivity), "
                    "and restricted to work areas. Sensitive personal information (medical "
                    "records, union membership) requires higher protection. National Privacy "
                    "Commission (NPC) has enforcement jurisdiction. Violations: imprisonment "
                    "of 1-3 years (unauthorized processing), 3-6 years (accessing with "
                    "malice), 1-5 years (improper disposal) and corresponding fines."
                ),
            },
        ],
        "sort_order": 41,
    },
]

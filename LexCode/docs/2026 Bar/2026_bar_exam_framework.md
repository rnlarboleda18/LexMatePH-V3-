# 2026 Bar examinations — framework for concept alignment

This file is a **structured study of what the LexMatePH stack already encodes** for the 2026 Bar, plus **official Supreme Court pointers**. It is **not** a full paste of the PDF syllabi; add those as separate `.txt` / `.md` files in this folder for stricter matching.

## Official sources (Supreme Court)

- Bar 2026 hub: https://sc.judiciary.gov.ph/bar-2026/
- Bar Bulletin No. 1 (conduct, schedule, syllabi): linked from the hub (October 2025).
- Bar Bulletin No. 2 (application, venues): December 2025 PDF on SC site.

## Examination subjects (Rule 138 framework)

Per SC rules, applicants are tested on:

1. Political and Public International Law  
2. Labor Law and Social Legislation  
3. Civil Law and Land Titles and Deeds  
4. Commercial and Taxation Laws  
5. Criminal Law  
6. Remedial Law, Legal and Judicial Ethics, with Practical Exercises  

**Schedule (typical three-day layout):**

- Day 1 AM: Political and Public International Law  
- Day 1 PM: Commercial and Taxation Laws  
- Day 2 AM: Civil Law and Land Titles and Deeds  
- Day 2 PM: Labor Law and Social Legislation  
- Day 3 AM: Criminal Law  
- Day 3 PM: Remedial Law, Legal and Judicial Ethics, with Practical Exercises  

**Relative weights (for averaging):**

- Political and Public International Law — 15%  
- Commercial and Taxation Laws — 20%  
- Civil Law and Land Titles and Deeds — 20%  
- Labor Law and Social Legislation — 10%  
- Criminal Law — 10%  
- Remedial Law, Legal and Judicial Ethics, with Practical Exercises — 25%  

## LexMatePH exam slots (question mix)

- Political + PIL: 17 + 3  
- Commercial + Taxation: 15 + 5  
- Civil + Land Titles: 16 + 4  
- Labor + Social Legislation: 16 + 4  
- Criminal + Special Penal: 16 + 4  
- Remedial + Ethics + Practical: weighted in the 25% bucket  

## Bar subject / sub-topic classifier (used in app)

Sub-topics a 2026 candidate should map concepts to:

- Political Law  
- Public International Law  
- Commercial Law  
- Taxation  
- Civil Law  
- Land Titles and Deeds  
- Labor Law  
- Social Legislation  
- Criminal Law  
- Special Penal Laws  
- Remedial Law  
- Legal and Judicial Ethics  
- Practical Exercises  

## Table-of-specifications style topics (JSON source: scripts/data/bar_tos_topics.json)

High-level topic blobs (keywords and narrative text in repo JSON) cover:

- Political / constitutional / international / bill of rights / judicial review  
- Civil: obligations, contracts, property, family, succession, torts, damages, prescription  
- Commercial: negotiable instruments, banking, insurance, corporations, securities, insolvency  
- Criminal: RPC, circumstances, penalties, special penal laws context  
- Labor: Labor Code, termination, unions, strikes, social security agencies  
- Remedial: RoC, jurisdiction, evidence, appeals, extraordinary writs  
- Taxation: NIRC, local taxation, assessment, customs  
- Legal ethics: CPRA, discipline, conflicts, notarial practice  

When classifying a digest **legal concept**, treat it as Bar-relevant if it would plausibly be tested under **any** subject or sub-topic above for the **2026** exam cycle.

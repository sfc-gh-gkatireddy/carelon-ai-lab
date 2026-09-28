#!/usr/bin/env python3
"""
Synthetic payer dataset generator for the Carelon AI Lab.
Produces 4 CSVs (members, medical claims, pharmacy claims, providers)
modelled on a commercial health plan population. 100% synthetic - no real
member, patient, or PHI data. Stdlib only.

Usage:  python3 generate_data.py [--outdir ../data] [--seed 42]
"""
import argparse
import csv
import datetime as dt
import os
import random
from collections import defaultdict

random.seed_arg = None  # placeholder to keep lint quiet

# ── Reference data ──────────────────────────────────────────────────────────

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Marcus",
    "Aisha", "Dwayne", "Keisha", "Robert", "Tanisha", "Malik", "Latoya",
    "Jerome", "Denise", "Andre", "Monica", "Trevon", "Kiara", "Jamal",
    "Renee", "Xavier", "Alyssa", "Dante", "Brianna", "Hassan", "Priya",
    "Wei", "Mei", "Carlos", "Sofia", "Luis", "Ana", "Miguel", "Lucia",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
    "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan",
    "Cooper", "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos",
    "Kim", "Cox", "Ward", "Richardson", "Watson", "Brooks", "Chavez",
    "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long",
    "Ross", "Foster", "Jimenez",
]

CHRONIC_CONDITIONS = [
    ("Diabetes", 0.14),
    ("Hypertension", 0.22),
    ("COPD", 0.06),
    ("Asthma", 0.07),
    ("Coronary Artery Disease", 0.05),
    ("Heart Failure", 0.04),
    ("Chronic Kidney Disease", 0.04),
    ("Depression", 0.09),
    ("Hyperlipidemia", 0.15),
    ("None", 0.14),
]

PLANS = [
    ("PLN-1001", "Blue Advantage HMO", "HMO"),
    ("PLN-1002", "Blue Advantage PPO", "PPO"),
    ("PLN-1003", "Blue Essential EPO", "EPO"),
    ("PLN-1004", "Blue High-Deductible PPO", "HDHP"),
    ("PLN-1005", "Blue Medicare Advantage HMO", "Medicare Advantage"),
    ("PLN-1006", "Blue Medicare Advantage PPO", "Medicare Advantage"),
]

STATES = [
    ("GA", "Atlanta", 0.22), ("GA", "Savannah", 0.06),
    ("CA", "Los Angeles", 0.12), ("CA", "San Diego", 0.06),
    ("CA", "San Francisco", 0.05), ("CA", "Sacramento", 0.04),
    ("NY", "New York", 0.12), ("NY", "Buffalo", 0.04), ("NY", "Albany", 0.03),
    ("MO", "St. Louis", 0.08), ("MO", "Kansas City", 0.06),
    ("VA", "Richmond", 0.05), ("VA", "Norfolk", 0.03),
    ("OH", "Columbus", 0.04),
]

# ICD-10 codes grouped by the condition that drives them
ICD10_BY_CONDITION = {
    "Diabetes": [("E11.9", "Type 2 diabetes without complications", 0.5),
                  ("E11.65", "Type 2 diabetes with hyperglycemia", 0.2),
                  ("E11.319", "Diabetic retinopathy", 0.15),
                  ("E11.40", "Diabetic neuropathy", 0.15)],
    "Hypertension": [("I10", "Essential hypertension", 0.7),
                      ("I11.9", "Hypertensive heart disease", 0.3)],
    "COPD": [("J44.1", "COPD with exacerbation", 0.6),
              ("J44.9", "COPD unspecified", 0.4)],
    "Asthma": [("J45.909", "Asthma unspecified, uncomplicated", 0.7),
                ("J45.21", "Mild intermittent asthma with exacerbation", 0.3)],
    "Coronary Artery Disease": [("I25.10", "Atherosclerotic heart disease", 0.7),
                                 ("I20.9", "Angina pectoris unspecified", 0.3)],
    "Heart Failure": [("I50.9", "Heart failure unspecified", 0.7),
                       ("I50.32", "Chronic diastolic heart failure", 0.3)],
    "Chronic Kidney Disease": [("N18.3", "CKD stage 3", 0.6),
                                ("N18.32", "CKD stage 3b", 0.4)],
    "Depression": [("F32.9", "Major depressive disorder single episode", 0.7),
                    ("F33.1", "Major depressive disorder recurrent moderate", 0.3)],
    "Hyperlipidemia": [("E78.5", "Hyperlipidemia unspecified", 1.0)],
    "Preventive": [("Z00.00", "Encounter for general adult exam", 0.5),
                    ("Z00.129", "Encounter for routine child health exam", 0.1),
                    ("Z23", "Encounter for immunization", 0.2),
                    ("Z12.11", "Encounter for colorectal cancer screening", 0.2)],
    "Acute": [("J06.9", "Acute upper respiratory infection", 0.25),
               ("I21.0", "Acute myocardial infarction", 0.05),
               ("J18.9", "Pneumonia", 0.15),
               ("S52.501", "Fracture of radius", 0.15),
               ("K35.80", "Acute appendicitis", 0.05),
               ("N39.0", "Urinary tract infection", 0.25),
               ("M54.50", "Low back pain", 0.10)],
    "Mental Health": [("F41.1", "Generalized anxiety disorder", 0.6),
                       ("F90.9", "ADHD unspecified", 0.2),
                       ("F31.81", "Bipolar II disorder", 0.2)],
}

# CPT codes: (code, description, service_type, base_cost)
PROCEDURES = [
    ("99391", "Preventive visit, established", "Preventive Care", 180),
    ("99395", "Preventive visit, periodic", "Preventive Care", 170),
    ("45378", "Colonoscopy, diagnostic", "Preventive Care", 1850),
    ("93000", "Electrocardiogram", "Office Visit", 60),
    ("99213", "Office visit, level 3", "Office Visit", 145),
    ("99214", "Office visit, level 4", "Office Visit", 210),
    ("99215", "Office visit, level 5", "Office Visit", 320),
    ("99284", "ER visit, level 4", "Emergency Room", 950),
    ("99285", "ER visit, level 5", "Emergency Room", 1450),
    ("45380", "Colonoscopy with biopsy", "Surgical", 2400),
    ("47562", "Laparoscopic cholecystectomy", "Surgical", 8900),
    ("29881", "Knee arthroscopy", "Surgical", 7200),
    ("27447", "Total knee replacement", "Surgical", 31000),
    ("93351", "Echocardiogram complete", "Diagnostic Imaging", 780),
    ("70450", "CT head/brain", "Diagnostic Imaging", 1050),
    ("71046", "Chest X-ray, 2 views", "Diagnostic Imaging", 210),
    ("74177", "CT abdomen/pelvis with contrast", "Diagnostic Imaging", 1380),
    ("96372", "Therapeutic injection", "Office Visit", 95),
    ("90834", "Psychotherapy, 45 min", "Mental Health", 165),
    ("90837", "Psychotherapy, 60 min", "Mental Health", 215),
    ("97110", "Physical therapy, therapeutic exercises", "Physical Therapy", 120),
    ("97140", "Manual therapy techniques", "Physical Therapy", 105),
    ("J1885", "Ketorolac injection", "Office Visit", 45),
    ("80053", "Comprehensive metabolic panel", "Lab", 55),
    ("85025", "Complete blood count", "Lab", 42),
    ("83036", "HbA1c", "Lab", 38),
    ("84443", "TSH assay", "Lab", 49),
]

DRUGS = [
    ("Metformin", "Biguanide", "500 mg", 28, 22),
    ("Metformin ER", "Biguanide", "750 mg", 28, 35),
    ("Glipizide", "Sulfonylurea", "10 mg", 28, 26),
    ("Insulin Glargine", "Insulin", "100 u/mL", 28, 310),
    ("Insulin Lispro", "Insulin", "100 u/mL", 28, 285),
    ("Semaglutide", "GLP-1 Agonist", "1 mg", 28, 1350),
    ("Liraglutide", "GLP-1 Agonist", "1.8 mg", 28, 1120),
    ("Tirzepatide", "GLP-1 Agonist", "10 mg", 28, 1490),
    ("Lisinopril", "ACE Inhibitor", "20 mg", 28, 14),
    ("Losartan", "ARB", "100 mg", 28, 18),
    ("Amlodipine", "Calcium Channel Blocker", "10 mg", 28, 16),
    ("Atorvastatin", "Statin", "40 mg", 28, 24),
    ("Rosuvastatin", "Statin", "20 mg", 28, 42),
    ("Ezetimibe", "Cholesterol Absorption Inhibitor", "10 mg", 28, 55),
    ("Albuterol HFA", "SABA", "90 mcg", 28, 65),
    ("Fluticasone/Salmeterol", "ICS/LABA", "250/50", 28, 320),
    ("Tiotropium", "LAMA", "18 mcg", 28, 265),
    ("Sertraline", "SSRI", "100 mg", 28, 12),
    ("Escitalopram", "SSRI", "20 mg", 28, 15),
    ("Bupropion XL", "NDRI", "300 mg", 28, 45),
    ("Sitagliptin", "DPP-4 Inhibitor", "100 mg", 28, 290),
    ("Empagliflozin", "SGLT2 Inhibitor", "25 mg", 28, 470),
    ("Dapagliflozin", "SGLT2 Inhibitor", "10 mg", 28, 445),
    ("Humalog Mix 75/25", "Insulin", "100 u/mL", 28, 265),
    ("Apixaban", "Anticoagulant", "5 mg", 28, 520),
    ("Furosemide", "Loop Diuretic", "40 mg", 28, 11),
    ("Pantoprazole", "PPI", "40 mg", 28, 21),
    ("Amoxicillin", "Antibiotic", "500 mg", 14, 14),
    ("Azithromycin", "Antibiotic", "250 mg", 5, 26),
    ("Prednisone", "Corticosteroid", "20 mg", 10, 9),
]

SPECIALTIES = [
    ("Internal Medicine", 0.16), ("Family Medicine", 0.16),
    ("Cardiology", 0.08), ("Endocrinology", 0.06),
    ("Pulmonology", 0.05), ("Nephrology", 0.04),
    ("Emergency Medicine", 0.08), ("Orthopedics", 0.07),
    ("Gastroenterology", 0.05), ("Psychiatry", 0.05),
    ("General Surgery", 0.05), ("Radiology", 0.04),
    ("Physical Therapy", 0.05), ("Oncology", 0.02),
    ("Ophthalmology", 0.04),
]

CLAIM_STATUS = [("Paid", 0.78), ("Denied", 0.08), ("Pending", 0.06),
                ("Adjusted", 0.05), ("Appealed", 0.03)]


def weighted_choice(items, weight_index=-1):
    total = sum(i[weight_index] for i in items)
    r = random.uniform(0, total)
    cum = 0
    for i in items:
        cum += i[weight_index]
        if r <= cum:
            return i
    return items[-1]


def rand_date(start, end):
    delta = (end - start).days
    return start + dt.timedelta(days=random.randint(0, delta))


def money(x):
    return round(x, 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    args = parser.parse_args()
    random.seed(args.seed)

    os.makedirs(args.outdir, exist_ok=True)

    today = dt.date(2026, 9, 1)
    two_years_ago = today - dt.timedelta(days=730)

    # ── Providers ────────────────────────────────────────────────────────────
    providers = []
    for i in range(1, 2001):
        spec = weighted_choice(SPECIALTIES)[0]
        state, city, _ = weighted_choice(STATES)
        network = "In-Network" if random.random() < 0.82 else "Out-of-Network"
        base_visit = {"Internal Medicine": 165, "Family Medicine": 155,
                      "Cardiology": 320, "Endocrinology": 280,
                      "Pulmonology": 300, "Nephrology": 310,
                      "Emergency Medicine": 1200, "Orthopedics": 340,
                      "Gastroenterology": 350, "Psychiatry": 260,
                      "General Surgery": 480, "Radiology": 290,
                      "Physical Therapy": 140, "Oncology": 520,
                      "Ophthalmology": 230}.get(spec, 200)
        avg_cost = money(base_visit * random.uniform(0.7, 1.6))
        providers.append({
            "provider_id": f"PRV-{i:06d}",
            "name": f"Dr. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}{' MD' if random.random() < 0.8 else ' DO'}",
            "specialty": spec,
            "npi": f"{random.randint(1000000000, 1999999999)}",
            "network_status": network,
            "location": f"{city}, {state}",
            "avg_cost_per_visit": avg_cost,
        })

    # ── Members ─────────────────────────────────────────────────────────────
    members = []
    member_conditions = {}
    for i in range(1, 10001):
        cond = weighted_choice(CHRONIC_CONDITIONS)[0]
        member_conditions[i] = cond
        plan = random.choice(PLANS)
        age = random.randint(18, 88) if "Medicare" not in plan[2] else random.randint(65, 92)
        dob = today - dt.timedelta(days=age * 365 + random.randint(0, 364))
        state, city, _ = weighted_choice(STATES)
        pcp = random.choice(providers)["provider_id"]
        enroll_start = rand_date(two_years_ago, today - dt.timedelta(days=30))
        enroll_end = enroll_start + dt.timedelta(days=365) if random.random() < 0.88 else ""
        smoker = "Y" if random.random() < (0.22 if cond in ("COPD", "Coronary Artery Disease", "Asthma") else 0.13) else "N"
        members.append({
            "member_id": f"MEM-{i:07d}",
            "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "dob": dob.isoformat(),
            "gender": random.choice(["M", "F", "M", "F", "X"]),
            "plan_id": plan[0],
            "plan_name": plan[1],
            "plan_type": plan[2],
            "pcp": pcp,
            "chronic_condition": cond,
            "smoker_ind": smoker,
            "enrollment_start": enroll_start.isoformat(),
            "enrollment_end": enroll_end if enroll_end else "",
            "state": state,
            "city": city,
        })

    # ── Medical Claims ──────────────────────────────────────────────────────
    # Higher utilisation for chronic members, scaled by condition severity
    severity = {"Diabetes": 2.2, "Hypertension": 1.6, "COPD": 2.4, "Asthma": 1.7,
                "Coronary Artery Disease": 2.6, "Heart Failure": 3.0,
                "Chronic Kidney Disease": 2.5, "Depression": 1.8,
                "Hyperlipidemia": 1.4, "None": 0.6}
    claims = []
    claim_id = 1
    for m in members:
        cond = member_conditions[int(m["member_id"].split("-")[1])]
        sev = severity.get(cond, 1.0)
        n = max(1, int(random.gauss(7 * sev, 3)))
        n = min(n, 40)
        for _ in range(n):
            proc = random.choice(PROCEDURES)
            # pick diagnosis: 55% tied to condition, rest general mix
            if cond != "None" and random.random() < 0.55:
                pool = ICD10_BY_CONDITION[cond]
            else:
                r = random.random()
                pool = (ICD10_BY_CONDITION["Preventive"] if r < 0.30 else
                        ICD10_BY_CONDITION["Acute"] if r < 0.80 else
                        ICD10_BY_CONDITION["Mental Health"])
            diag = weighted_choice(pool)
            provider = random.choice(providers)
            service_date = rand_date(two_years_ago, today)
            status = weighted_choice(CLAIM_STATUS)[0]
            billed = money(proc[3] * random.uniform(0.8, 1.5))
            allowed = money(billed * random.uniform(0.55, 0.75))
            paid = money(allowed * (random.uniform(0.0, 0.05) if status == "Denied"
                                    else random.uniform(0.90, 1.0)))
            claims.append({
                "claim_id": f"CLM-{claim_id:08d}",
                "member_id": m["member_id"],
                "service_date": service_date.isoformat(),
                "provider_id": provider["provider_id"],
                "icd10_code": diag[0],
                "icd10_desc": diag[1],
                "procedure_code": proc[0],
                "procedure_desc": proc[1],
                "billed_amt": billed,
                "allowed_amt": allowed,
                "paid_amt": paid,
                "claim_status": status,
                "service_type": proc[2],
            })
            claim_id += 1

    # ── Pharmacy Claims ───────────────────────────────────────────────────────
    # Chronic members get maintenance fills; GLP-1s skew to diabetes/obesity
    drug_by_condition = {
        "Diabetes": ["Metformin", "Metformin ER", "Glipizide", "Insulin Glargine",
                      "Insulin Lispro", "Semaglutide", "Liraglutide", "Tirzepatide",
                      "Sitagliptin", "Empagliflozin", "Dapagliflozin", "Humalog Mix 75/25"],
        "Hypertension": ["Lisinopril", "Losartan", "Amlodipine"],
        "COPD": ["Albuterol HFA", "Fluticasone/Salmeterol", "Tiotropium", "Prednisone"],
        "Asthma": ["Albuterol HFA", "Fluticasone/Salmeterol"],
        "Coronary Artery Disease": ["Atorvastatin", "Rosuvastatin", "Ezetimibe", "Apixaban"],
        "Heart Failure": ["Furosemide", "Lisinopril"],
        "Chronic Kidney Disease": ["Lisinopril", "Furosemide"],
        "Depression": ["Sertraline", "Escitalopram", "Bupropion XL"],
        "Hyperlipidemia": ["Atorvastatin", "Rosuvastatin", "Ezetimibe"],
        "None": ["Amoxicillin", "Azithromycin", "Pantoprazole", "Prednisone"],
    }
    drug_lookup = {d[0]: d for d in DRUGS}
    rx = []
    rx_id = 1
    for m in members:
        cond = member_conditions[int(m["member_id"].split("-")[1])]
        drugs = drug_by_condition[cond]
        n_drugs = len(drugs) if cond != "None" else 1
        n_fills = max(1, int(n_drugs * random.uniform(0.8, 2.2)))
        for _ in range(n_fills):
            drug = drug_lookup[random.choice(drugs)]
            fill_date = rand_date(two_years_ago, today)
            unit_paid = money(drug[4] * random.uniform(0.85, 1.15))
            paid = money(unit_paid * random.choice([1, 1, 2]) / 1)
            prescriber = random.choice(providers)
            ndc = f"{random.randint(10000000, 99999999):08d}"
            rx.append({
                "rx_id": f"RX-{rx_id:08d}",
                "member_id": m["member_id"],
                "drug_name": drug[0],
                "ndc_code": ndc,
                "drug_class": drug[1],
                "drug_strength": drug[2],
                "days_supply": drug[3] * random.choice([1, 1, 1, 2, 3]),
                "paid_amt": paid,
                "fill_date": fill_date.isoformat(),
                "prescriber_id": prescriber["provider_id"],
            })
            rx_id += 1

    # ── Write CSVs ────────────────────────────────────────────────────────────
    def write_csv(path, rows, fieldnames):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows):>7} rows -> {path}")

    write_csv(os.path.join(args.outdir, "members.csv"), members,
              ["member_id", "name", "dob", "gender", "plan_id", "plan_name",
               "plan_type", "pcp", "chronic_condition", "smoker_ind",
               "enrollment_start", "enrollment_end", "state", "city"])
    write_csv(os.path.join(args.outdir, "medical_claims.csv"), claims,
              ["claim_id", "member_id", "service_date", "provider_id",
               "icd10_code", "icd10_desc", "procedure_code", "procedure_desc",
               "billed_amt", "allowed_amt", "paid_amt", "claim_status",
               "service_type"])
    write_csv(os.path.join(args.outdir, "pharmacy_claims.csv"), rx,
              ["rx_id", "member_id", "drug_name", "ndc_code", "drug_class",
               "drug_strength", "days_supply", "paid_amt", "fill_date",
               "prescriber_id"])
    write_csv(os.path.join(args.outdir, "providers.csv"), providers,
              ["provider_id", "name", "specialty", "npi", "network_status",
               "location", "avg_cost_per_visit"])


if __name__ == "__main__":
    main()

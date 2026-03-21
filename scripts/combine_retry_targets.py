import re

# Read not updated cases
with open("audit_not_updated.txt", "r") as f:
    not_updated = set(line.strip() for line in f if line.strip())

# Read non-compliant cases (extract IDs from "case_id: reason" format)
with open("audit_non_compliant.txt", "r") as f:
    non_compliant = set()
    for line in f:
        if line.strip():
            match = re.match(r"(\d+):", line)
            if match:
                non_compliant.add(match.group(1))

# Combine both sets
all_targets = sorted(not_updated | non_compliant, key=int)

# Write to new target file
with open("target_retry_facts.txt", "w") as f:
    f.write("\n".join(all_targets))

print(f"Combined target list created:")
print(f"  Not Updated:     {len(not_updated)}")
print(f"  Non-Compliant:   {len(non_compliant)}")
print(f"  Total to Retry:  {len(all_targets)}")
print(f"  Saved to: target_retry_facts.txt")

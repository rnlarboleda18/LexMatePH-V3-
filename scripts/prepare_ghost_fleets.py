def main():
    # Load all ghost IDs
    try:
        with open('undigested_full_text_cases.txt', 'r') as f:
            all_ghosts = set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        print("Error: undigested_full_text_cases.txt not found. Please run deep_audit_undigested.py first.")
        return

    # Load En Banc IDs
    try:
        with open('ghost_enbanc_ids.txt', 'r') as f:
            enbanc_ghosts = set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        print("Error: ghost_enbanc_ids.txt not found. Please run analyze_ghost_enbanc.py first.")
        return

    # Calculate Division Ghosts (Remaining)
    division_ghosts = all_ghosts - enbanc_ghosts

    print(f"Total Ghost Cases: {len(all_ghosts)}")
    print(f"En Banc Ghosts: {len(enbanc_ghosts)}")
    print(f"Division Ghosts (Remaining): {len(division_ghosts)}")

    # Save to files
    with open('ghost_fleet_enbanc.txt', 'w') as f:
        for mid in sorted(list(enbanc_ghosts)):
            f.write(f"{mid}\n")
    
    with open('ghost_fleet_division.txt', 'w') as f:
        for mid in sorted(list(division_ghosts)):
            f.write(f"{mid}\n")

    print("\nFiles created:")
    print("- ghost_fleet_enbanc.txt")
    print("- ghost_fleet_division.txt")

if __name__ == "__main__":
    main()

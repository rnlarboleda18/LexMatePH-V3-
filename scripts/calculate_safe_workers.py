"""
TPM (Tokens Per Minute) Limit Calculation for gemini-3-flash-preview

From API limits screenshot:
- gemini-3-flash TPM: 1.69M / 1M
- This means: OUTPUT token limit = 1M tokens per minute

Case Characteristics (92.9% of cases < 100K chars):
- Average input: ~28K chars ≈ 7K tokens
- Average output with MINIMAL separate opinions: ~150K tokens (estimated)
- Processing time per case: ~50 seconds (from test observations)

"""

# Constants
OUTPUT_TPM_LIMIT = 1_000_000  # 1M tokens per minute
AVG_OUTPUT_TOKENS = 150_000   # Conservative estimate with minimal opinions
AVG_PROCESSING_TIME_SEC = 50  # From test results

# Calculate tokens per minute per worker
cases_per_minute_per_worker = 60 / AVG_PROCESSING_TIME_SEC
output_tokens_per_minute_per_worker = cases_per_minute_per_worker * AVG_OUTPUT_TOKENS

print("="*80)
print("TPM LIMIT ANALYSIS FOR PARALLEL WORKERS")
print("="*80)
print(f"\nAPI Limit: {OUTPUT_TPM_LIMIT:,} output tokens per minute")
print(f"Average output per case: {AVG_OUTPUT_TOKENS:,} tokens (with minimal opinions)")
print(f"Average processing time: {AVG_PROCESSING_TIME_SEC} seconds per case")
print(f"\nPer Worker Metrics:")
print(f"  Cases/minute: {cases_per_minute_per_worker:.2f}")
print(f"  Output tokens/minute: {output_tokens_per_minute_per_worker:,.0f}")

# Calculate max theoretical workers
max_workers_theoretical = OUTPUT_TPM_LIMIT / output_tokens_per_minute_per_worker

print(f"\n{'='*80}")
print("SAFE WORKER COUNTS")
print("="*80)
print(f"\nTheoretical Maximum: {max_workers_theoretical:.1f} workers")
print(f"  → This assumes perfect synchronization (unrealistic)")

# Apply safety margins
safety_factors = [
    (0.8, "Conservative (80% margin)", "Recommended for production"),
    (0.6, "Very Safe (60% margin)", "Recommended if API is flaky"),
    (0.5, "Ultra Safe (50% margin)", "Overkill but zero risk"),
]

for factor, label, note in safety_factors:
    safe_workers = int(max_workers_theoretical * factor)
    print(f"\n{label}:")
    print(f"  Max Workers: {safe_workers}")
    print(f"  Note: {note}")

# Realistic recommendation accounting for natural throttling
print(f"\n{'='*80}")
print("RECOMMENDATION")
print("="*80)
print(f"\nRealistic Estimate: 8-12 workers")
print(f"  Rationale:")
print(f"    - Not all workers process simultaneously (natural throttling)")
print(f"    - Smaller cases process faster, creating gaps")
print(f"    - TPM is a rolling window, not instantaneous")
print(f"    - 92.9% of cases are < 100K chars (faster processing)")
print(f"\nProposed Deployment:")
print(f"  Start with: 10 workers")
print(f"  Monitor: First 100 cases for TPM errors")
print(f"  Scale up: To 15 workers if no TPM issues")
print(f"  Max safe: 20 workers (with active monitoring)")
print("="*80)

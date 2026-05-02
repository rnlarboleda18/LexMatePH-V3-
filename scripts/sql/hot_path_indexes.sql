-- Optional indexes for heavy LexMatePH routes.
-- Run during low traffic. CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
--
-- Inspect seq scans first:
--   SELECT relname, seq_scan, idx_scan
--   FROM pg_stat_user_tables
--   ORDER BY seq_scan DESC
--   LIMIT 40;

-- Codal ↔ case links (paragraph-level counts, juris queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_codal_case_links_statute_provision
  ON codal_case_links (statute_id, provision_id);

-- Supreme Court decisions: date-ordered lists and filters
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sc_decided_cases_date_id
  ON sc_decided_cases (date DESC NULLS LAST, id DESC);

-- Uncomment after confirming column names match WHERE clauses in api/blueprints:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_civ_codal_article_num ON civ_codal (article_num);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rpc_codal_article_num ON rpc_codal (article_num);

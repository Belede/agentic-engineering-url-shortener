-- Migration 0002: optional max_clicks limit (CL-02, brownfield scenario).
-- Nullable, backward-compatible — existing rows get NULL (unlimited).
ALTER TABLE short_links ADD COLUMN max_clicks INTEGER;

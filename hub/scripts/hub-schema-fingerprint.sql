-- JV hub schema fingerprint: one sorted text line per schema fact of the
-- public.orchestration_* objects (columns, constraints, indexes, views, RLS).
-- Run on two databases and diff the output; the parity gate expects an empty
-- diff except the declared deltas in migrations/0001_baseline.sql (policies).
-- Read-only catalog query.
SELECT line FROM (
  SELECT format('col %s.%s #%s %s null=%s default=%s',
           c.relname, a.attname, a.attnum, format_type(a.atttypid, a.atttypmod),
           NOT a.attnotnull, coalesce(pg_get_expr(d.adbin, d.adrelid), '-')) AS line
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
  WHERE n.nspname = 'public' AND c.relname LIKE 'orchestration\_%'
    AND c.relkind IN ('r', 'v') AND a.attnum > 0 AND NOT a.attisdropped
  UNION ALL
  SELECT format('con %s %s %s', c.relname, con.conname, pg_get_constraintdef(con.oid))
  FROM pg_constraint con
  JOIN pg_class c ON c.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relname LIKE 'orchestration\_%'
  UNION ALL
  SELECT format('idx %s', pg_get_indexdef(i.indexrelid))
  FROM pg_index i
  JOIN pg_class c ON c.oid = i.indrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relname LIKE 'orchestration\_%'
  UNION ALL
  SELECT format('view %s %s', c.relname, md5(pg_get_viewdef(c.oid, true)))
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relname LIKE 'orchestration\_%' AND c.relkind = 'v'
  UNION ALL
  SELECT format('rls %s enabled=%s forced=%s', c.relname, c.relrowsecurity, c.relforcerowsecurity)
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relname LIKE 'orchestration\_%' AND c.relkind = 'r'
  UNION ALL
  SELECT format('policy %s %s', tablename, policyname)
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename LIKE 'orchestration\_%'
) f
ORDER BY line;

-- JV hub, postgrest backend: 0001 baseline (orchestration_* tables + views).
--
-- Provenance: pg_dump --schema-only --no-owner --no-privileges of public.orchestration_*
-- from a local Supabase substrate built from JAuto customer-portal origin/staging
-- 6f31f45dd (all JA hub migrations 20260517221227..20260717090000 applied), 2026-09-23.
--
-- Declared deltas vs the JAuto staging hub (hub-separation plan PLAN.md §2.3 step 1):
--   * RLS stays ENABLED on every table, but the JAuto read policies are dropped: they
--     call public.is_super_admin(), which reads the product `users` table. Service-role
--     bypasses RLS; anon/authenticated are denied by default.
--   * No GRANTs to anon/authenticated (dumped with --no-privileges).
--   * No supabase_realtime publication membership (no realtime consumer).
--   * ci_scenario_lock_holder / ci_scenario_lock_active() are JAuto CI state and stay in JAuto.
--
-- Column order is byte-for-byte the dump's attnum order so CSV exports from the JAuto hub
-- import with `\copy <table> FROM ... CSV HEADER` unchanged (hub/scripts/hub-snapshot.sh).

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: orchestration_attention; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_attention (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    severity text NOT NULL,
    category text NOT NULL,
    title text NOT NULL,
    body text,
    refs_dispatch_id uuid,
    refs_pr integer,
    refs_issue integer,
    hub_id text,
    metadata jsonb,
    CONSTRAINT orchestration_attention_category_check CHECK ((category = ANY (ARRAY['blocked'::text, 'awaiting_decision'::text, 'idle_with_queue'::text, 'ci_red'::text, 'manual'::text, 'ingest_reject'::text]))),
    CONSTRAINT orchestration_attention_severity_check CHECK ((severity = ANY (ARRAY['info'::text, 'warn'::text, 'blocking'::text])))
);

--
-- Name: TABLE orchestration_attention; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.orchestration_attention IS 'Epic #2249 — items needing Justin''s eyes. Open rows surface in Sprint 2 ATTN strip.';

--
-- Name: orchestration_dispatches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_dispatches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    to_role character(1) NOT NULL,
    from_role character(1),
    title text NOT NULL,
    body text,
    issue_number integer,
    pr_number integer,
    epic_number integer,
    scope_class text,
    status text NOT NULL,
    blocked_reason text,
    prereq_dispatch_ids uuid[] DEFAULT '{}'::uuid[] NOT NULL,
    dispatched_at timestamp with time zone,
    acked_at timestamp with time zone,
    done_at timestamp with time zone,
    shipped_sha text,
    planned_for timestamp with time zone,
    source text NOT NULL,
    source_msg_ts timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    thread_id text,
    hub_id text,
    CONSTRAINT orchestration_dispatches_scope_class_check CHECK ((scope_class = ANY (ARRAY['Quick'::text, 'Standard'::text, 'M'::text, 'L'::text, 'XL'::text]))),
    CONSTRAINT orchestration_dispatches_source_check CHECK ((source = ANY (ARRAY['manual'::text, 'ingester'::text, 'skill'::text]))),
    CONSTRAINT orchestration_dispatches_status_check CHECK ((status = ANY (ARRAY['planned'::text, 'dispatched'::text, 'acked'::text, 'in_flight'::text, 'blocked'::text, 'review'::text, 'staged'::text, 'prod'::text, 'done'::text, 'cancelled'::text])))
);

--
-- Name: TABLE orchestration_dispatches; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.orchestration_dispatches IS 'Epic #2249 — unit of work assignment; status taxonomy drives Sprint 2 board.';

--
-- Name: orchestration_findings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_findings (
    id text NOT NULL,
    hub_id text,
    title text NOT NULL,
    body text,
    suggested_thread_id text,
    routed_at timestamp with time zone,
    source_msg_ts timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: orchestration_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_roles (
    letter character(1) NOT NULL,
    kind text NOT NULL,
    worktree_path text,
    current_branch text,
    head_sha text,
    has_uncommitted boolean DEFAULT false NOT NULL,
    ports jsonb,
    status text NOT NULL,
    cadence_seconds integer,
    last_signal_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_heartbeat_at timestamp with time zone,
    wake_count integer DEFAULT 0 NOT NULL,
    wake_state text,
    is_fixture boolean DEFAULT false NOT NULL,
    CONSTRAINT orchestration_roles_kind_check CHECK ((kind = ANY (ARRAY['orchestrator'::text, 'integrator'::text, 'implementer'::text]))),
    CONSTRAINT orchestration_roles_letter_check CHECK ((letter ~ '^[A-Z]$'::text)),
    CONSTRAINT orchestration_roles_status_check CHECK ((status = ANY (ARRAY['active'::text, 'idle'::text, 'parked'::text, 'retired'::text]))),
    CONSTRAINT orchestration_roles_wake_state_check CHECK (((wake_state IS NULL) OR (wake_state = ANY (ARRAY['awake'::text, 'sleeping'::text, 'standby'::text]))))
);

--
-- Name: TABLE orchestration_roles; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.orchestration_roles IS 'Epic #2249 — persistent role identity (one row per active letter A-Z plus O/I).';

--
-- Name: COLUMN orchestration_roles.last_heartbeat_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.orchestration_roles.last_heartbeat_at IS 'Last wake-tick time (from the role''s cadence file via the ingester). Distinct from last_signal_at (= last message). O''s liveness signal. #2606';

--
-- Name: COLUMN orchestration_roles.wake_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.orchestration_roles.wake_count IS 'Monotonic per-role wake-loop counter. Detects alive-and-advancing vs frozen. #2606';

--
-- Name: COLUMN orchestration_roles.wake_state; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.orchestration_roles.wake_state IS 'Wake-loop phase: awake (mid-cycle) | sleeping (between cycles) | standby (all tasks parked, awaiting dispatch). Distinct axis from status (lifecycle). #2606, #2957';

--
-- Name: COLUMN orchestration_roles.is_fixture; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.orchestration_roles.is_fixture IS '#2968: row was written by test/fixture machinery — operator surfaces (attention_feed overdue_role) exclude it. Real seats are status=''active'' AND NOT is_fixture; the letter allowlist is retired.';

--
-- Name: orchestration_role_liveness; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.orchestration_role_liveness WITH (security_invoker='true') AS
 SELECT letter,
    kind,
    status,
    wake_state,
    wake_count,
    last_heartbeat_at,
    last_signal_at,
    cadence_seconds,
    (EXTRACT(epoch FROM (now() - last_heartbeat_at)))::integer AS seconds_since_heartbeat,
    ((last_heartbeat_at IS NULL) OR ((now() - last_heartbeat_at) > make_interval(secs => (GREATEST((COALESCE(cadence_seconds, 900) * 2), 1200))::double precision))) AS is_stale
   FROM public.orchestration_roles;

--
-- Name: VIEW orchestration_role_liveness; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.orchestration_role_liveness IS 'Per-role liveness for O: seconds_since_heartbeat + is_stale (no heartbeat within GREATEST(2x cadence_seconds, 1200s floor)). #2606';

--
-- Name: orchestration_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_threads (
    id text NOT NULL,
    hub_id text,
    title text NOT NULL,
    intent_anchor text NOT NULL,
    anchor_source text,
    owner_role character(1),
    state text DEFAULT 'live'::text NOT NULL,
    lane text,
    "grouping" jsonb DEFAULT '[]'::jsonb NOT NULL,
    next_gate text,
    last_event_at timestamp with time zone,
    links jsonb DEFAULT '{"prs": [], "docs": [], "issues": [], "decisions": []}'::jsonb NOT NULL,
    source_msg_ts timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    depends_on text[] DEFAULT '{}'::text[] NOT NULL,
    checklist jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT orchestration_threads_state_check CHECK ((state = ANY (ARRAY['live'::text, 'parked'::text, 'dead'::text, 'shipped'::text])))
);

--
-- Name: orchestration_attention_feed; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.orchestration_attention_feed WITH (security_invoker='true') AS
 SELECT 'overdue_role'::text AS source_kind,
    'warn'::text AS severity,
    (l.letter)::text AS ref_id,
    NULL::text AS ref_thread_id,
    NULL::integer AS ref_pr,
    NULL::integer AS ref_issue,
    (('Role '::text || (l.letter)::text) || ' stale — no heartbeat within liveness window'::text) AS title,
        CASE
            WHEN (l.last_heartbeat_at IS NULL) THEN 'No heartbeat ever recorded.'::text
            ELSE (((('Last heartbeat '::text || to_char(l.last_heartbeat_at, 'YYYY-MM-DD HH24:MI:SS TZ'::text)) || ' ('::text) || l.seconds_since_heartbeat) || 's ago).'::text)
        END AS body,
    l.last_heartbeat_at AS event_at,
    NULL::text AS category,
    NULL::jsonb AS metadata
   FROM (public.orchestration_role_liveness l
     JOIN public.orchestration_roles r ON ((r.letter = l.letter)))
  WHERE (l.is_stale AND (r.status = 'active'::text) AND (NOT r.is_fixture) AND ((r.current_branch IS NULL) OR ((r.current_branch !~~ '%__TDS_TEST__%'::text) AND (r.current_branch !~~ '%tds-fixture%'::text))))
UNION ALL
 SELECT 'stalled_thread'::text AS source_kind,
    'warn'::text AS severity,
    t.id AS ref_id,
    t.id AS ref_thread_id,
    NULL::integer AS ref_pr,
    NULL::integer AS ref_issue,
    (('Thread "'::text || t.title) || '" stalled — no event in 6h'::text) AS title,
        CASE
            WHEN (t.last_event_at IS NULL) THEN 'Live thread with no recorded event yet.'::text
            ELSE (('Last event '::text || to_char(t.last_event_at, 'YYYY-MM-DD HH24:MI:SS TZ'::text)) || '.'::text)
        END AS body,
    t.last_event_at AS event_at,
    NULL::text AS category,
    NULL::jsonb AS metadata
   FROM public.orchestration_threads t
  WHERE ((t.state = 'live'::text) AND (COALESCE(t.last_event_at, t.created_at) < (now() - '06:00:00'::interval)))
UNION ALL
 SELECT 'pending_gate'::text AS source_kind,
        CASE
            WHEN (d.status = 'blocked'::text) THEN 'blocking'::text
            ELSE 'info'::text
        END AS severity,
    (d.id)::text AS ref_id,
    d.thread_id AS ref_thread_id,
    d.pr_number AS ref_pr,
    d.issue_number AS ref_issue,
    ((('Dispatch '::text || d.status) || ': '::text) || d.title) AS title,
    COALESCE(d.blocked_reason, d.body) AS body,
    COALESCE(d.updated_at, d.created_at) AS event_at,
    NULL::text AS category,
    NULL::jsonb AS metadata
   FROM public.orchestration_dispatches d
  WHERE (d.status = ANY (ARRAY['blocked'::text, 'review'::text]))
UNION ALL
 SELECT 'unrouted_finding'::text AS source_kind,
    'info'::text AS severity,
    f.id AS ref_id,
    f.suggested_thread_id AS ref_thread_id,
    NULL::integer AS ref_pr,
    NULL::integer AS ref_issue,
    ('Unrouted finding: '::text || f.title) AS title,
    f.body,
    f.created_at AS event_at,
    NULL::text AS category,
    NULL::jsonb AS metadata
   FROM public.orchestration_findings f
  WHERE (f.routed_at IS NULL)
UNION ALL
 SELECT 'dispatch_without_thread'::text AS source_kind,
    'info'::text AS severity,
    (d.id)::text AS ref_id,
    NULL::text AS ref_thread_id,
    d.pr_number AS ref_pr,
    d.issue_number AS ref_issue,
    ('Dispatch not linked to a thread: '::text || d.title) AS title,
    NULL::text AS body,
    COALESCE(d.updated_at, d.created_at) AS event_at,
    NULL::text AS category,
    NULL::jsonb AS metadata
   FROM public.orchestration_dispatches d
  WHERE ((d.thread_id IS NULL) AND (d.status <> ALL (ARRAY['done'::text, 'cancelled'::text, 'blocked'::text, 'review'::text])))
UNION ALL
 SELECT 'manual'::text AS source_kind,
    a.severity,
    (a.id)::text AS ref_id,
    NULL::text AS ref_thread_id,
    a.refs_pr AS ref_pr,
    a.refs_issue AS ref_issue,
    a.title,
    a.body,
    a.created_at AS event_at,
    a.category,
    a.metadata
   FROM public.orchestration_attention a
  WHERE (a.resolved_at IS NULL);

--
-- Name: VIEW orchestration_attention_feed; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.orchestration_attention_feed IS 'Orchestration Hub S1 (#2842 §5): O''s one-query attention read — UNION of overdue roles, stalled threads, pending gates, unrouted findings, dispatch-without-thread hygiene, and open manual attention. Thresholds are v1 view constants (6h stalled window). security_invoker pushes RLS to base tables.';

--
-- Name: orchestration_docs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_docs (
    id text NOT NULL,
    hub_id text,
    doc_path text NOT NULL,
    kind text,
    thread_id text,
    source_msg_ts timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT orchestration_docs_kind_check CHECK ((kind = ANY (ARRAY['spec'::text, 'scope'::text, 'plan'::text, 'memory'::text])))
);

--
-- Name: orchestration_journal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_journal (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    authored_at timestamp with time zone DEFAULT now() NOT NULL,
    author_role character(1),
    category text NOT NULL,
    title text NOT NULL,
    body text,
    refs_pr integer[] DEFAULT '{}'::integer[] NOT NULL,
    refs_issue integer[] DEFAULT '{}'::integer[] NOT NULL,
    refs_commit text[] DEFAULT '{}'::text[] NOT NULL,
    refs_dispatch_id uuid,
    supersedes_id text,
    thread_id text,
    hub_id text,
    source_msg_ts timestamp with time zone,
    CONSTRAINT orchestration_journal_category_check CHECK ((category = ANY (ARRAY['decision'::text, 'milestone'::text, 'pattern'::text, 'note'::text, 'incident'::text, 'broadcast'::text])))
);

--
-- Name: TABLE orchestration_journal; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.orchestration_journal IS 'Epic #2249 — decisions, milestones, broadcasts. Append-only narrative ledger.';

--
-- Name: orchestration_status_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orchestration_status_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dispatch_hub_id text NOT NULL,
    from_status text,
    to_status text NOT NULL,
    at timestamp with time zone NOT NULL,
    hub_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: TABLE orchestration_status_events; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.orchestration_status_events IS 'Epic #2249 S2-P0 — append-only dispatch status-transition log (honest time-in-status for the seats view). One row per drained hub status op; dedup on the op hub_id; service-role write, super_admin read.';

--
-- Name: orchestration_attention orchestration_attention_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_attention
    ADD CONSTRAINT orchestration_attention_pkey PRIMARY KEY (id);

--
-- Name: orchestration_dispatches orchestration_dispatches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_dispatches
    ADD CONSTRAINT orchestration_dispatches_pkey PRIMARY KEY (id);

--
-- Name: orchestration_docs orchestration_docs_hub_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_docs
    ADD CONSTRAINT orchestration_docs_hub_id_key UNIQUE (hub_id);

--
-- Name: orchestration_docs orchestration_docs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_docs
    ADD CONSTRAINT orchestration_docs_pkey PRIMARY KEY (id);

--
-- Name: orchestration_findings orchestration_findings_hub_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_findings
    ADD CONSTRAINT orchestration_findings_hub_id_key UNIQUE (hub_id);

--
-- Name: orchestration_findings orchestration_findings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_findings
    ADD CONSTRAINT orchestration_findings_pkey PRIMARY KEY (id);

--
-- Name: orchestration_journal orchestration_journal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_journal
    ADD CONSTRAINT orchestration_journal_pkey PRIMARY KEY (id);

--
-- Name: orchestration_roles orchestration_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_roles
    ADD CONSTRAINT orchestration_roles_pkey PRIMARY KEY (letter);

--
-- Name: orchestration_status_events orchestration_status_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_status_events
    ADD CONSTRAINT orchestration_status_events_pkey PRIMARY KEY (id);

--
-- Name: orchestration_threads orchestration_threads_hub_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_threads
    ADD CONSTRAINT orchestration_threads_hub_id_key UNIQUE (hub_id);

--
-- Name: orchestration_threads orchestration_threads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_threads
    ADD CONSTRAINT orchestration_threads_pkey PRIMARY KEY (id);

--
-- Name: orchestration_attention_hub_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX orchestration_attention_hub_id_key ON public.orchestration_attention USING btree (hub_id) WHERE (hub_id IS NOT NULL);

--
-- Name: orchestration_attention_open_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_attention_open_idx ON public.orchestration_attention USING btree (severity, created_at DESC) WHERE (resolved_at IS NULL);

--
-- Name: orchestration_dispatches_hub_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX orchestration_dispatches_hub_id_key ON public.orchestration_dispatches USING btree (hub_id) WHERE (hub_id IS NOT NULL);

--
-- Name: orchestration_dispatches_planned_for_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_dispatches_planned_for_idx ON public.orchestration_dispatches USING btree (planned_for) WHERE (planned_for IS NOT NULL);

--
-- Name: orchestration_dispatches_pr_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_dispatches_pr_number_idx ON public.orchestration_dispatches USING btree (pr_number) WHERE (pr_number IS NOT NULL);

--
-- Name: orchestration_dispatches_thread_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_dispatches_thread_id_idx ON public.orchestration_dispatches USING btree (thread_id);

--
-- Name: orchestration_dispatches_to_role_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_dispatches_to_role_status_idx ON public.orchestration_dispatches USING btree (to_role, status);

--
-- Name: orchestration_findings_unrouted_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_findings_unrouted_idx ON public.orchestration_findings USING btree (routed_at) WHERE (routed_at IS NULL);

--
-- Name: orchestration_journal_authored_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_journal_authored_at_idx ON public.orchestration_journal USING btree (authored_at DESC);

--
-- Name: orchestration_journal_hub_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX orchestration_journal_hub_id_key ON public.orchestration_journal USING btree (hub_id) WHERE (hub_id IS NOT NULL);

--
-- Name: orchestration_journal_thread_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_journal_thread_id_idx ON public.orchestration_journal USING btree (thread_id);

--
-- Name: orchestration_roles_heartbeat_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_roles_heartbeat_idx ON public.orchestration_roles USING btree (last_heartbeat_at DESC NULLS LAST);

--
-- Name: orchestration_roles_status_signal_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_roles_status_signal_idx ON public.orchestration_roles USING btree (status, last_signal_at DESC);

--
-- Name: orchestration_status_events_dispatch_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_status_events_dispatch_at_idx ON public.orchestration_status_events USING btree (dispatch_hub_id, at);

--
-- Name: orchestration_status_events_hub_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX orchestration_status_events_hub_id_key ON public.orchestration_status_events USING btree (hub_id) WHERE (hub_id IS NOT NULL);

--
-- Name: orchestration_threads_last_event_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_threads_last_event_idx ON public.orchestration_threads USING btree (last_event_at);

--
-- Name: orchestration_threads_state_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX orchestration_threads_state_idx ON public.orchestration_threads USING btree (state);

--
-- Name: orchestration_attention orchestration_attention_refs_dispatch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_attention
    ADD CONSTRAINT orchestration_attention_refs_dispatch_id_fkey FOREIGN KEY (refs_dispatch_id) REFERENCES public.orchestration_dispatches(id) ON DELETE SET NULL;

--
-- Name: orchestration_dispatches orchestration_dispatches_from_role_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_dispatches
    ADD CONSTRAINT orchestration_dispatches_from_role_fkey FOREIGN KEY (from_role) REFERENCES public.orchestration_roles(letter);

--
-- Name: orchestration_dispatches orchestration_dispatches_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_dispatches
    ADD CONSTRAINT orchestration_dispatches_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.orchestration_threads(id);

--
-- Name: orchestration_dispatches orchestration_dispatches_to_role_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_dispatches
    ADD CONSTRAINT orchestration_dispatches_to_role_fkey FOREIGN KEY (to_role) REFERENCES public.orchestration_roles(letter);

--
-- Name: orchestration_docs orchestration_docs_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_docs
    ADD CONSTRAINT orchestration_docs_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.orchestration_threads(id);

--
-- Name: orchestration_findings orchestration_findings_suggested_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_findings
    ADD CONSTRAINT orchestration_findings_suggested_thread_id_fkey FOREIGN KEY (suggested_thread_id) REFERENCES public.orchestration_threads(id);

--
-- Name: orchestration_journal orchestration_journal_author_role_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_journal
    ADD CONSTRAINT orchestration_journal_author_role_fkey FOREIGN KEY (author_role) REFERENCES public.orchestration_roles(letter);

--
-- Name: orchestration_journal orchestration_journal_refs_dispatch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_journal
    ADD CONSTRAINT orchestration_journal_refs_dispatch_id_fkey FOREIGN KEY (refs_dispatch_id) REFERENCES public.orchestration_dispatches(id) ON DELETE SET NULL;

--
-- Name: orchestration_journal orchestration_journal_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_journal
    ADD CONSTRAINT orchestration_journal_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.orchestration_threads(id);

--
-- Name: orchestration_threads orchestration_threads_owner_role_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orchestration_threads
    ADD CONSTRAINT orchestration_threads_owner_role_fkey FOREIGN KEY (owner_role) REFERENCES public.orchestration_roles(letter);

--
-- Name: orchestration_attention; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_attention ENABLE ROW LEVEL SECURITY;

--
-- Name: orchestration_dispatches; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_dispatches ENABLE ROW LEVEL SECURITY;

--
-- Name: orchestration_docs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_docs ENABLE ROW LEVEL SECURITY;

--
-- Name: orchestration_findings; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_findings ENABLE ROW LEVEL SECURITY;

--
-- Name: orchestration_journal; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_journal ENABLE ROW LEVEL SECURITY;

--
-- Name: orchestration_roles; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_roles ENABLE ROW LEVEL SECURITY;

--
-- Name: orchestration_status_events; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_status_events ENABLE ROW LEVEL SECURITY;

--
-- Name: orchestration_threads; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.orchestration_threads ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--


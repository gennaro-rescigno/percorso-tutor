# Probe di fly-trader-seed
dump: 2.29 GB
pg_restore: pg_restore (PostgreSQL) 18.6 (Ubuntu 18.6-1.pgdg24.04+2)

## Indice del dump
```
;
; Archive created at 2026-09-22 18:59:55 UTC
;     dbname: fly_trader
;     TOC Entries: 204
;     Compression: gzip
;     Dump Version: 1.16-0
;     Format: CUSTOM
;     Integer: 4 bytes
;     Offset: 8 bytes
;     Dumped from database version: 17.11 (Homebrew)
;     Dumped by pg_dump version: 17.11 (Homebrew)
;
;
; Selected TOC Entries:
;
449; 1259 7236380 SEQUENCE public api_calls_id_seq bryce
470; 1259 7246122 TABLE public beat_slots_20260706 bryce
471; 1259 7246130 TABLE public beat_slots_20260707 bryce
475; 1259 7246540 TABLE public beat_slots_20260714 bryce
476; 1259 7246548 TABLE public beat_slots_20260715 bryce
463; 1259 7236490 TABLE public beat_slots_20260911 bryce
464; 1259 7236498 TABLE public beat_slots_20260912 bryce
465; 1259 7236506 TABLE public beat_slots_20260913 bryce
466; 1259 7236514 TABLE public beat_slots_20260914 bryce
499; 1259 7348603 TABLE public beat_slots_20260915 bryce
534; 1259 7594608 TABLE public beat_slots_20260916 bryce
560; 1259 7763259 TABLE public beat_slots_20260917 bryce
589; 1259 7787827 TABLE public beat_slots_20260918 bryce
590; 1259 7787835 TABLE public beat_slots_20260919 bryce
591; 1259 7787843 TABLE public beat_slots_20260920 bryce
592; 1259 7787851 TABLE public beat_slots_20260921 bryce
599; 1259 7788773 TABLE public beat_slots_20260922 bryce
606; 1259 7793264 TABLE public beat_slots_20260923 bryce
425; 1259 7236212 SEQUENCE public beats_id_seq bryce
440; 1259 7236318 SEQUENCE public brain_snapshots_id_seq bryce
445; 1259 7236359 SEQUENCE public circuit_events_id_seq bryce
508; 1259 7429791 TABLE public corpus_features bryce
518; 1259 7506070 TABLE public corpus_meta bryce
506; 1259 7417013 TABLE public corpus_tokens bryce
429; 1259 7236238 SEQUENCE public decisions_id_seq bryce
451; 1259 7236392 SEQUENCE public events_id_seq bryce
433; 1259 7236266 SEQUENCE public fills_id_seq bryce
571; 1259 7784030 SEQUENCE public fly_rollbacks_id_seq bryce
521; 1259 7509087 TABLE public mature_days bryce
447; 1259 7236369 SEQUENCE public notional_ledger_id_seq bryce
431; 1259 7236252 SEQUENCE public orders_id_seq bryce
435; 1259 7236278 SEQUENCE public positions_id_seq bryce
454; 1259 7236412 SEQUENCE public processes_id_seq bryce
531; 1259 7594582 TABLE public pump_events bryce
530; 1259 7594574 TABLE public pump_minutes bryce
542; 1259 7654362 TABLE public pump_pools bryce
516; 1259 7474279 TABLE public replay_days bryce
513; 1259 7471926 TABLE public replay_hours bryce
413; 1259 7236119 TABLE public schema_version bryce
420; 1259 7236172 SEQUENCE public swap_tape_id_seq bryce
578; 1259 7785414 TABLE public token_insiders bryce
418; 1259 7236150 TABLE public token_stats bryce
417; 1259 7236149 SEQUENCE public token_stats_id_seq bryce
5039; 0 0 SEQUENCE OWNED BY public token_stats_id_seq bryce
416; 1259 7236137 TABLE public tokens bryce
414; 1259 7236127 SEQUENCE public wallet_events_id_seq bryce
4606; 0 0 TABLE ATTACH public beat_slots_20260706 bryce
4607; 0 0 TABLE ATTACH public beat_slots_20260707 bryce
4608; 0 0 TABLE ATTACH public beat_slots_20260714 bryce
4609; 0 0 TABLE ATTACH public beat_slots_20260715 bryce
4602; 0 0 TABLE ATTACH public beat_slots_20260911 bryce
4603; 0 0 TABLE ATTACH public beat_slots_20260912 bryce
4604; 0 0 TABLE ATTACH public beat_slots_20260913 bryce
4605; 0 0 TABLE ATTACH public beat_slots_20260914 bryce
4610; 0 0 TABLE ATTACH public beat_slots_20260915 bryce
4611; 0 0 TABLE ATTACH public beat_slots_20260916 bryce
4612; 0 0 TABLE ATTACH public beat_slots_20260917 bryce
4613; 0 0 TABLE ATTACH public beat_slots_20260918 bryce
4614; 0 0 TABLE ATTACH public beat_slots_20260919 bryce
4615; 0 0 TABLE ATTACH public beat_slots_20260920 bryce
4616; 0 0 TABLE ATTACH public beat_slots_20260921 bryce
4617; 0 0 TABLE ATTACH public beat_slots_20260922 bryce
4618; 0 0 TABLE ATTACH public beat_slots_20260923 bryce
4626; 2604 7236153 DEFAULT public token_stats id bryce
5009; 0 7246122 TABLE DATA public beat_slots_20260706 bryce
5010; 0 7246130 TABLE DATA public beat_slots_20260707 bryce
5011; 0 7246540 TABLE DATA public beat_slots_20260714 bryce
5012; 0 7246548 TABLE DATA public beat_slots_20260715 bryce
5005; 0 7236490 TABLE DATA public beat_slots_20260911 bryce
5006; 0 7236498 TABLE DATA public beat_slots_20260912 bryce
5007; 0 7236506 TABLE DATA public beat_slots_20260913 bryce
5008; 0 7236514 TABLE DATA public beat_slots_20260914 bryce
5013; 0 7348603 TABLE DATA public beat_slots_20260915 bryce
5022; 0 7594608 TABLE DATA public beat_slots_20260916 bryce
5024; 0 7763259 TABLE DATA public beat_slots_20260917 bryce
5027; 0 7787827 TABLE DATA public beat_slots_20260918 bryce
5028; 0 7787835 TABLE DATA public beat_slots_20260919 bryce
5029; 0 7787843 TABLE DATA public beat_slots_20260920 bryce
5030; 0 7787851 TABLE DATA public beat_slots_20260921 bryce
5031; 0 7788773 TABLE DATA public beat_slots_20260922 bryce
5032; 0 7793264 TABLE DATA public beat_slots_20260923 bryce
5015; 0 7429791 TABLE DATA public corpus_features bryce
5018; 0 7506070 TABLE DATA public corpus_meta bryce
5014; 0 7417013 TABLE DATA public corpus_tokens bryce
5019; 0 7509087 TABLE DATA public mature_days bryce
5021; 0 7594582 TABLE DATA public pump_events bryce
5020; 0 7594574 TABLE DATA public pump_minutes bryce
5023; 0 7654362 TABLE DATA public pump_pools bryce
5017; 0 7474279 TABLE DATA public replay_days bryce
5016; 0 7471926 TABLE DATA public replay_hours bryce
4988; 0 7236119 TABLE DATA public schema_version bryce
5026; 0 7785414 TABLE DATA public token_insiders bryce
4992; 0 7236150 TABLE DATA public token_stats bryce
4990; 0 7236137 TABLE DATA public tokens bryce
5040; 0 0 SEQUENCE SET public api_calls_id_seq bryce
5041; 0 0 SEQUENCE SET public beats_id_seq bryce
5042; 0 0 SEQUENCE SET public brain_snapshots_id_seq bryce
5043; 0 0 SEQUENCE SET public circuit_events_id_seq bryce
5044; 0 0 SEQUENCE SET public decisions_id_seq bryce
5045; 0 0 SEQUENCE SET public events_id_seq bryce
5046; 0 0 SEQUENCE SET public fills_id_seq bryce
5047; 0 0 SEQUENCE SET public fly_rollbacks_id_seq bryce
5048; 0 0 SEQUENCE SET public notional_ledger_id_seq bryce
5049; 0 0 SEQUENCE SET public orders_id_seq bryce
5050; 0 0 SEQUENCE SET public positions_id_seq bryce
5051; 0 0 SEQUENCE SET public processes_id_seq bryce
5052; 0 0 SEQUENCE SET public swap_tape_id_seq bryce
5053; 0 0 SEQUENCE SET public token_stats_id_seq bryce
5054; 0 0 SEQUENCE SET public wallet_events_id_seq bryce
4743; 2606 7246126 CONSTRAINT public beat_slots_20260706 beat_slots_20260706_pkey bryce
4746; 2606 7246134 CONSTRAINT public beat_slots_20260707 beat_slots_20260707_pkey bryce
4749; 2606 7246544 CONSTRAINT public beat_slots_20260714 beat_slots_20260714_pkey bryce
4752; 2606 7246552 CONSTRAINT public beat_slots_20260715 beat_slots_20260715_pkey bryce
4731; 2606 7236494 CONSTRAINT public beat_slots_20260911 beat_slots_20260911_pkey bryce
4734; 2606 7236502 CONSTRAINT public beat_slots_20260912 beat_slots_20260912_pkey bryce
4737; 2606 7236510 CONSTRAINT public beat_slots_20260913 beat_slots_20260913_pkey bryce
4740; 2606 7236518 CONSTRAINT public beat_slots_20260914 beat_slots_20260914_pkey bryce
4755; 2606 7348607 CONSTRAINT public beat_slots_20260915 beat_slots_20260915_pkey bryce
4780; 2606 7594612 CONSTRAINT public beat_slots_20260916 beat_slots_20260916_pkey bryce
4786; 2606 7763263 CONSTRAINT public beat_slots_20260917 beat_slots_20260917_pkey bryce
4793; 2606 7787831 CONSTRAINT public beat_slots_20260918 beat_slots_20260918_pkey bryce
4796; 2606 7787839 CONSTRAINT public beat_slots_20260919 beat_slots_20260919_pkey bryce
4799; 2606 7787847 CONSTRAINT public beat_slots_20260920 beat_slots_20260920_pkey bryce
4802; 2606 7787855 CONSTRAINT public beat_slots_20260921 beat_slots_20260921_pkey bryce
4805; 2606 7788777 CONSTRAINT public beat_slots_20260922 beat_slots_20260922_pkey bryce
4808; 2606 7793268 CONSTRAINT public beat_slots_20260923 beat_slots_20260923_pkey bryce
4760; 2606 7429798 CONSTRAINT public corpus_features corpus_features_pkey bryce
4768; 2606 7506077 CONSTRAINT public corpus_meta corpus_meta_pkey bryce
4757; 2606 7417023 CONSTRAINT public corpus_tokens corpus_tokens_pkey bryce
4770; 2606 7509092 CONSTRAINT public mature_days mature_days_pkey bryce
4777; 2606 7594588 CONSTRAINT public pump_events pump_events_pkey bryce
4772; 2606 7594580 CONSTRAINT public pump_minutes pump_minutes_pkey bryce
4783; 2606 7654369 CONSTRAINT public pump_pools pump_pools_pkey bryce
4764; 2606 7474284 CONSTRAINT public replay_days replay_days_pkey bryce
4762; 2606 7471934 CONSTRAINT public replay_hours replay_hours_pkey bryce
4674; 2606 7236126 CONSTRAINT public schema_version schema_version_pkey bryce
4790; 2606 7785420 CONSTRAINT public token_insiders token_insiders_pkey bryce
4683; 2606 7236158 CONSTRAINT public token_stats token_stats_pkey bryce
4679; 2606 7236146 CONSTRAINT public tokens tokens_pkey bryce
4741; 1259 7246127 INDEX public beat_slots_20260706_mint_ts_idx bryce
4744; 1259 7246135 INDEX public beat_slots_20260707_mint_ts_idx bryce
4747; 1259 7246545 INDEX public beat_slots_20260714_mint_ts_idx bryce
4750; 1259 7246553 INDEX public beat_slots_20260715_mint_ts_idx bryce
4729; 1259 7236495 INDEX public beat_slots_20260911_mint_ts_idx bryce
4732; 1259 7236503 INDEX public beat_slots_20260912_mint_ts_idx bryce
4735; 1259 7236511 INDEX public beat_slots_20260913_mint_ts_idx bryce
4738; 1259 7236519 INDEX public beat_slots_20260914_mint_ts_idx bryce
4753; 1259 7348608 INDEX public beat_slots_20260915_mint_ts_idx bryce
4778; 1259 7594613 INDEX public beat_slots_20260916_mint_ts_idx bryce
4784; 1259 7763264 INDEX public beat_slots_20260917_mint_ts_idx bryce
4791; 1259 7787832 INDEX public beat_slots_20260918_mint_ts_idx bryce
4794; 1259 7787840 INDEX public beat_slots_20260919_mint_ts_idx bryce
4797; 1259 7787848 INDEX public beat_slots_20260920_mint_ts_idx bryce
4800; 1259 7787856 INDEX public beat_slots_20260921_mint_ts_idx bryce
4803; 1259 7788778 INDEX public beat_slots_20260922_mint_ts_idx bryce
4806; 1259 7793269 INDEX public beat_slots_20260923_mint_ts_idx bryce
4765; 1259 7619543 INDEX public corpus_meta_creator_g_idx bryce
4766; 1259 7506078 INDEX public corpus_meta_creator_idx bryce
4758; 1259 7417024 INDEX public corpus_tokens_status_idx bryce
4774; 1259 7619544 INDEX public pump_events_creates_idx bryce
4775; 1259 7594589 INDEX public pump_events_mint_idx bryce
4773; 1259 7594581 INDEX public pump_minutes_ts_idx bryce
4781; 1259 7654370 INDEX public pump_pools_mint_idx bryce
4681; 1259 7236159 INDEX public token_stats_mint_ts_idx bryce
4677; 1259 7236147 INDEX public tokens_graduated_at_idx bryce
4680; 1259 7236148 INDEX public tokens_watch_status_idx bryce
4817; 0 0 INDEX ATTACH public beat_slots_20260706_mint_ts_idx bryce
4818; 0 0 INDEX ATTACH public beat_slots_20260706_pkey bryce
4819; 0 0 INDEX ATTACH public beat_slots_20260707_mint_ts_idx bryce
4820; 0 0 INDEX ATTACH public beat_slots_20260707_pkey bryce
4821; 0 0 INDEX ATTACH public beat_slots_20260714_mint_ts_idx bryce
4822; 0 0 INDEX ATTACH public beat_slots_20260714_pkey bryce
4823; 0 0 INDEX ATTACH public beat_slots_20260715_mint_ts_idx bryce
4824; 0 0 INDEX ATTACH public beat_slots_20260715_pkey bryce
4809; 0 0 INDEX ATTACH public beat_slots_20260911_mint_ts_idx bryce
4810; 0 0 INDEX ATTACH public beat_slots_20260911_pkey bryce
4811; 0 0 INDEX ATTACH public beat_slots_20260912_mint_ts_idx bryce
4812; 0 0 INDEX ATTACH public beat_slots_20260912_pkey bryce
4813; 0 0 INDEX ATTACH public beat_slots_20260913_mint_ts_idx bryce
4814; 0 0 INDEX ATTACH public beat_slots_20260913_pkey bryce
4815; 0 0 INDEX ATTACH public beat_slots_20260914_mint_ts_idx bryce
4816; 0 0 INDEX ATTACH public beat_slots_20260914_pkey bryce
4825; 0 0 INDEX ATTACH public beat_slots_20260915_mint_ts_idx bryce
4826; 0 0 INDEX ATTACH public beat_slots_20260915_pkey bryce
4827; 0 0 INDEX ATTACH public beat_slots_20260916_mint_ts_idx bryce
4828; 0 0 INDEX ATTACH public beat_slots_20260916_pkey bryce
4829; 0 0 INDEX ATTACH public beat_slots_20260917_mint_ts_idx bryce
4830; 0 0 INDEX ATTACH public beat_slots_20260917_pkey bryce
4831; 0 0 INDEX ATTACH public beat_slots_20260918_mint_ts_idx bryce
4832; 0 0 INDEX ATTACH public beat_slots_20260918_pkey bryce
4833; 0 0 INDEX ATTACH public beat_slots_20260919_mint_ts_idx bryce
4834; 0 0 INDEX ATTACH public beat_slots_20260919_pkey bryce
4835; 0 0 INDEX ATTACH public beat_slots_20260920_mint_ts_idx bryce
4836; 0 0 INDEX ATTACH public beat_slots_20260920_pkey bryce
4837; 0 0 INDEX ATTACH public beat_slots_20260921_mint_ts_idx bryce
4838; 0 0 INDEX ATTACH public beat_slots_20260921_pkey bryce
4839; 0 0 INDEX ATTACH public beat_slots_20260922_mint_ts_idx bryce
4840; 0 0 INDEX ATTACH public beat_slots_20260922_pkey bryce
4841; 0 0 INDEX ATTACH public beat_slots_20260923_mint_ts_idx bryce
4842; 0 0 INDEX ATTACH public beat_slots_20260923_pkey bryce

```

## Tabelle
```

--
-- Name: beat_slots_20260706; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260706 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260707; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260707 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260714; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260714 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260715; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260715 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260911; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260911 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260912; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260912 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260913; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260913 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260914; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260914 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260915; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260915 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260916; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260916 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260917; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260917 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260918; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260918 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260919; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260919 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260920; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260920 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260921; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260921 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260922; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260922 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: beat_slots_20260923; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.beat_slots_20260923 (
    beat_id bigint NOT NULL,
    slot smallint NOT NULL,
    ts timestamp with time zone NOT NULL,
    mint text,
    pool text,
    dwell_beats integer,
    features real[],
    feature_mask bigint,
    danger real,
    portfolio real[],
    glomeruli real[],
    stim real[],
    kc_active_frac real,
    m_hat real,
    rho_app real,
    rho_av real,
    dan_rew real,
    dan_pun real,
    delta_in real,
    decision_kind text,
    decision_size real,
    softmax_p real
);

--
-- Name: corpus_features; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.corpus_features (
    mint text NOT NULL,
    built_at timestamp with time zone DEFAULT now() NOT NULL,
    rows integer,
    trade_rows integer,
    has_trades boolean,
    path text
);

--
-- Name: corpus_meta; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.corpus_meta (
    mint text NOT NULL,
    create_ts timestamp with time zone,
    creator text,
    dev_sol double precision,
    dev_tokens double precision,
    dev_share real,
    supply double precision,
    mayhem boolean,
    uri text,
    name text,
    symbol text,
    ttg_min double precision,
    rq0 double precision,
    pool_id text,
    prior_launches integer,
    prior_grads integer,
    prior_known integer,
    prior_rug_share real,
    prior_moon_share real,
    own_dd60 real,
    own_max60 real,
    own_alive6h boolean,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    graduated_at timestamp with time zone,
    bundle_share real,
    dev_hold_share real,
    dev_sold_frac real,
    grad_hhi real,
    curve_known boolean
);

--
-- Name: corpus_tokens; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.corpus_tokens (
    mint text NOT NULL,
    graduated_at timestamp with time zone NOT NULL,
    grad_sig text,
    grad_slot bigint,
    source text DEFAULT 'migration_wallet'::text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    life_h double precision,
    candles_1m integer,
    candles_5m integer,
    trades integer,
    trades_through timestamp with time zone,
    candle_path text,
    trade_path text,
    last_error text,
    added_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: mature_days; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.mature_days (
    day date NOT NULL,
    mints integer,
    rows integer,
    took_s real,
    built_at timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: pump_events; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.pump_events (
    sig text NOT NULL,
    ts timestamp with time zone NOT NULL,
    action text NOT NULL,
    pool text,
    mint text,
    pool_id text,
    signer text,
    dev_sol double precision,
    dev_tokens double precision,
    supply double precision,
    mayhem boolean,
    quote_in_pool double precision,
    name text,
    symbol text,
    uri text
);

--
-- Name: pump_minutes; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.pump_minutes (
    mint text NOT NULL,
    ts timestamp with time zone NOT NULL,
    pool_id text,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    buy_sol double precision,
    sell_sol double precision,
    n_buys integer,
    n_sells integer,
    n_traders integer,
    resq_sol double precision,
    fee_rate double precision,
    n_buyers integer,
    wash_sol double precision,
    wash_buy_sol double precision,
    top_sell_sol double precision,
    insider_sell_sol double precision,
    skill_buy real[]
);

--
-- Name: pump_pools; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.pump_pools (
    pool_id text NOT NULL,
    mint text,
    created_by text,
    ts timestamp with time zone,
    source text NOT NULL,
    added_at timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: replay_days; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.replay_days (
    day date NOT NULL,
    graduations integer,
    tokens_written integer,
    took_s real,
    assembled_at timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: replay_hours; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.replay_hours (
    hour timestamp with time zone NOT NULL,
    status text DEFAULT 'done'::text NOT NULL,
    trades integer,
    events integer,
    bytes bigint,
    took_s real,
    last_error text,
    done_at timestamp with time zone DEFAULT now() NOT NULL
);

--
-- Name: schema_version; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.schema_version (
    singleton boolean DEFAULT true NOT NULL,
    version bigint NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT schema_version_singleton_check CHECK (singleton)
);

--
-- Name: token_insiders; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.token_insiders (
    mint text NOT NULL,
    wallet text NOT NULL,
    kind text NOT NULL
);

--
-- Name: token_stats; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.token_stats (
    id bigint NOT NULL,
    mint text NOT NULL,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    organic_score real,
    organic_label text,
    holder_count integer,
    liquidity_usd double precision,
    usd_price double precision,
    mcap double precision,
    top_holders_pct real,
    dev_balance_pct real,
    dev_mints integer,
    is_sus boolean,
    mint_auth_disabled boolean,
    freeze_auth_disabled boolean,
    is_verified boolean,
    stats jsonb
);


--
-- Name: tokens; Type: TABLE; Schema: public; Owner: bryce
--

CREATE TABLE public.tokens (
    mint text NOT NULL,
    symbol text,
    name text,
    decimals integer,
    token_program text,
    launchpad text,
    partner_config text,
    graduated_pool text,
    graduated_at timestamp with time zone,
    first_pool_id text,
    first_pool_created_at timestamp with time zone,
    mint_auth_disabled boolean,
    freeze_auth_disabled boolean,
    first_seen timestamp with time zone DEFAULT now() NOT NULL,
    last_seen timestamp with time zone DEFAULT now() NOT NULL,
    watch_status text DEFAULT 'candidate'::text NOT NULL,
    raw jsonb
)
```

## pump_minutes: prime righe
```
--
-- PostgreSQL database dump
--
\restrict s5Uhc1qwDZ8cCNAYtHX9sqTqIIXCmAbHzEnYcA8gzeWZIGXdVngslf3df0fCOOa
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

## corpus_tokens: prime righe
```
--
-- PostgreSQL database dump
--
\restrict m4L63hFZjgqTp9duqdT5PzvsLlVXahIhJaNfA9JluMmX5EWOEUE4psIBYthAnoi
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

## corpus_features: prime righe
```
--
-- PostgreSQL database dump
--
\restrict CuiBdKGRSj1s7iODdfQGod0TlfOEK7gxDo9cTkY12u9Udpf70v2fWUdvHHfjaJt
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

## pump_pools: prime righe
```
--
-- PostgreSQL database dump
--
\restrict 5oqBop1kZxRfbKxqe4nXtoVyQ6lWxDPXX7DTQqrI4plREnQAFNgQVL5iR7nCXDB
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

## pump_events: prime righe
```
--
-- PostgreSQL database dump
--
\restrict jaSa3f5MdS5U0yti3760VAPoJ73a4betjJHZTidPC13Ptv8rrP8q9g2u2A5ftC8
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

## tokens: prime righe
```
--
-- PostgreSQL database dump
--
\restrict DIyRlwmpWLbPscKAfwFXs2GHMPBELJsPeuyDBCAksiCfodyqa109VdHOPsRWq4M
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

## token_insiders: prime righe
```
--
-- PostgreSQL database dump
--
\restrict BOw27vlPW0LOTtrBpGAnwV4y6ht4S2EIxNKcgjz8kWkoVESQq4uh2cwhzbzDZlK
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

## mature_days: prime righe
```
--
-- PostgreSQL database dump
--
\restrict aFl12sOFP06otNahWeYOFxHHpxmiiemLh3f6G4L3GOb24aTRIlVpgpSr6voAFNQ
-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

```

from pathlib import Path

import yaml
from openpyxl import load_workbook


CONFIG_TEMPLATE = """
logging:
  level: INFO
  format: '%(message)s'
output:
  format: markdown
  log_dir: ./logs
  cache_dir: ./cache
  report_dir: ./reports
  filename_prefix: metadata_redundancy
scan:
  enable_cache: false
  lookback_hours: 24
  schedule: '0 23 * * *'
  similarity_threshold: 0.60
  candidate_similarity_threshold: 0.3
database:
  host: localhost
  port: 3306
  database: test
  username: test
  password: test
  charset: utf8mb4
  connection_timeout: 1
  read_timeout: 1
llm:
  base_url: http://example
  model_name: dummy
  api_key: ''
metadata_fields:
  primary_key: METADATA_ID
table_names:
  current: metadata
  audit: metadata_audit
  history: metadata_his
""".strip()


def _make_config(tmp_path, extra: str = ""):
    config_path = tmp_path / "config.yaml"
    content = CONFIG_TEMPLATE
    if extra:
        content = content + "\n" + extra.strip()
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_get_recent_metadata_changes_queries_only_audit_table(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    inform = MetadataChangeInform(str(_make_config(tmp_path)))
    captured = {"query": None}

    class DummyCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            captured["query"] = query

        def fetchall(self):
            return []

    class DummyConn:
        def cursor(self, *args, **kwargs):
            return DummyCursor()

    inform.db_connection = DummyConn()
    inform.get_recent_metadata_changes()

    normalized = " ".join(captured["query"].split()).lower()
    assert " from metadata_audit" in normalized
    assert " union" not in normalized
    assert " from metadata where" not in normalized


def test_hard_code_comparison_prefers_best_id_match_when_chinese_names_tie(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    inform = MetadataChangeInform(str(_make_config(tmp_path)))
    changed = [{
        'METADATA_ID': 'AcctActvtFlg_A',
        'METADATA_NAME': 'AcctActvtFlg_A',
        'CHINESE_NAME': '账户激活标识',
        'TYPE': 'string',
        'LENGTH': '1',
    }]
    current = [
        {
            'METADATA_ID': 'AcctStatusFlag',
            'METADATA_NAME': 'AcctStatusFlag',
            'CHINESE_NAME': '账户激活标识',
            'TYPE': 'string',
            'LENGTH': '1',
        },
        {
            'METADATA_ID': 'AcctActvtFlg_B',
            'METADATA_NAME': 'AcctActvtFlg_B',
            'CHINESE_NAME': '账户激活标识',
            'TYPE': 'string',
            'LENGTH': '1',
        },
    ]

    results, unmatched = inform._hard_code_driven_comparison(changed, current, threshold=0.70)
    assert unmatched == []
    assert len(results) == 1
    assert results[0]['existing_metadata']['METADATA_ID'] == 'AcctActvtFlg_B'


def test_current_config_uses_lowercase_table_names_from_project_config():
    config = yaml.safe_load(
        Path('/home/admin/Claude/requirement-estimation-system/metachange_inform/config.yaml').read_text(encoding='utf-8')
    )
    assert config['table_names']['current'] == 'metadata'
    assert config['table_names']['audit'] == 'metadata_audit'


def test_short_duplicate_chinese_name_uses_id_tie_break_over_first_match(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    inform = MetadataChangeInform(str(_make_config(tmp_path)))
    changed = [{
        'METADATA_ID': 'AbnTp',
        'METADATA_NAME': 'AbnTp',
        'CHINESE_NAME': '异常类型',
        'TYPE': 'String',
        'LENGTH': '24',
    }]
    current = [
        {
            'METADATA_ID': 'RiskTypeCode',
            'METADATA_NAME': 'RiskTypeCode',
            'CHINESE_NAME': '异常类型',
            'TYPE': 'String',
            'LENGTH': '24',
        },
        {
            'METADATA_ID': 'AbnTpCd',
            'METADATA_NAME': 'AbnTpCd',
            'CHINESE_NAME': '异常类型',
            'TYPE': 'String',
            'LENGTH': '24',
        },
    ]

    results, unmatched = inform._hard_code_driven_comparison(changed, current, threshold=0.60)
    assert unmatched == []
    assert len(results) == 1
    assert results[0]['existing_metadata']['METADATA_ID'] == 'AbnTpCd'


def test_type_and_length_do_not_override_chinese_name_plus_id_primary_match(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    inform = MetadataChangeInform(str(_make_config(tmp_path)))
    changed = [{
        'METADATA_ID': 'AcctActvtFlg_A',
        'METADATA_NAME': 'AcctActvtFlg_A',
        'CHINESE_NAME': '账户激活标识',
        'TYPE': 'string',
        'LENGTH': '1',
    }]
    current = [
        {
            'METADATA_ID': 'AcctActvtFlg_B',
            'METADATA_NAME': 'AcctActvtFlg_B',
            'CHINESE_NAME': '账户激活标识',
            'TYPE': 'int',
            'LENGTH': '10',
        },
        {
            'METADATA_ID': 'RiskStatusFlag',
            'METADATA_NAME': 'RiskStatusFlag',
            'CHINESE_NAME': '风险状态标识',
            'TYPE': 'string',
            'LENGTH': '1',
        },
    ]

    results, unmatched = inform._hard_code_driven_comparison(changed, current, threshold=0.60)
    assert unmatched == []
    assert len(results) == 1
    assert results[0]['existing_metadata']['METADATA_ID'] == 'AcctActvtFlg_B'


def test_high_frequency_short_chinese_name_penalty_prefers_more_specific_name(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    inform = MetadataChangeInform(str(_make_config(tmp_path, "scan:\n  similarity_threshold: 0.55\n  candidate_similarity_threshold: 0.3")))
    changed = [{
        'METADATA_ID': 'AbCdVal',
        'METADATA_NAME': 'AbCdVal',
        'CHINESE_NAME': '码值',
        'TYPE': 'String',
        'LENGTH': '32',
    }]
    current = [
        {'METADATA_ID': 'RiskLevelCode', 'METADATA_NAME': 'RiskLevelCode', 'CHINESE_NAME': '码值', 'TYPE': 'String', 'LENGTH': '32'},
        {'METADATA_ID': 'AbCdCode', 'METADATA_NAME': 'AbCdCode', 'CHINESE_NAME': '码值', 'TYPE': 'String', 'LENGTH': '32'},
        {'METADATA_ID': 'TxnRiskNo', 'METADATA_NAME': 'TxnRiskNo', 'CHINESE_NAME': '码值', 'TYPE': 'String', 'LENGTH': '32'},
    ]

    results, unmatched = inform._hard_code_driven_comparison(changed, current, threshold=0.55)
    assert unmatched == []
    assert len(results) == 1
    assert results[0]['existing_metadata']['METADATA_ID'] == 'AbCdCode'
    assert '高频中文名降权' in results[0]['reason']
    assert '短中文名降权' in results[0]['reason']


def test_env_variables_override_metachange_config(tmp_path, monkeypatch):
    from metachange_inform.metachange_inform import MetadataChangeInform

    config_path = _make_config(tmp_path)
    monkeypatch.setenv('METACHANGE_DB_HOST', '127.0.0.1')
    monkeypatch.setenv('METACHANGE_DB_PORT', '3307')
    monkeypatch.setenv('METACHANGE_DB_NAME', 'metachange_test')
    monkeypatch.setenv('METACHANGE_DB_USER', 'root')
    monkeypatch.setenv('METACHANGE_DB_PASSWORD', 'Mysql3306')
    monkeypatch.setenv('METACHANGE_LLM_BASE_URL', 'http://127.0.0.1:9999/v1')
    monkeypatch.setenv('METACHANGE_LLM_MODEL', 'local-model')
    monkeypatch.setenv('METACHANGE_LLM_API_KEY', 'local-key')

    inform = MetadataChangeInform(str(config_path))
    assert inform.config['database']['host'] == '127.0.0.1'
    assert inform.config['database']['port'] == 3307
    assert inform.config['database']['database'] == 'metachange_test'
    assert inform.config['database']['username'] == 'root'
    assert inform.config['database']['password'] == 'Mysql3306'
    assert inform.config['llm']['base_url'] == 'http://127.0.0.1:9999/v1'
    assert inform.config['llm']['model_name'] == 'local-model'
    assert inform.config['llm']['api_key'] == 'local-key'


def test_generate_candidates_method_exists_and_returns_ranked_candidates(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    inform = MetadataChangeInform(str(_make_config(tmp_path)))
    changed = {
        'METADATA_ID': 'AbCdVal',
        'METADATA_NAME': 'AbCdVal',
        'CHINESE_NAME': '码值',
        'TYPE': 'String',
        'LENGTH': '32',
    }
    current = [
        {'METADATA_ID': 'AbCdCode', 'METADATA_NAME': 'AbCdCode', 'CHINESE_NAME': '码值', 'TYPE': 'String', 'LENGTH': '32'},
        {'METADATA_ID': 'RiskLevelCode', 'METADATA_NAME': 'RiskLevelCode', 'CHINESE_NAME': '风险等级代码', 'TYPE': 'String', 'LENGTH': '32'},
    ]

    candidates = inform._generate_candidates(changed, current)
    assert len(candidates) >= 1
    assert candidates[0][0]['METADATA_ID'] == 'AbCdCode'


def test_generate_report_accepts_raw_changed_meta_list_without_key_error(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    inform = MetadataChangeInform(str(_make_config(tmp_path)))
    changed = [
        {'METADATA_ID': 'A1', 'CHINESE_NAME': '主商户号', 'TYPE': 'String', 'LENGTH': '64', 'OPT_TIME': '2026-03-27 11:00:43', 'OPT_USER': 'tester'},
        {'METADATA_ID': 'A2', 'CHINESE_NAME': '主订单号', 'TYPE': 'String', 'LENGTH': '64', 'OPT_TIME': '2026-03-27 10:59:34', 'OPT_USER': 'tester'},
    ]
    redundancy_results = [
        {
            'changed_metadata': changed[0],
            'existing_metadata': {'METADATA_ID': 'B1', 'CHINESE_NAME': '商户主编号'},
            'similarity_score': 0.88,
            'redundancy_level': '高',
            'reason': '综合相似度高(0.88)',
            'detection_time': '2026-03-27 15:00:00',
        }
    ]

    report = inform.generate_report(redundancy_results, changed)
    assert '# 元数据冗余分析报告' in report
    assert '| A1 | 主商户号 |' in report
    assert '| A2 | 主订单号 |' in report


def test_env_backend_internal_values_can_drive_llm_runtime_without_yaml_change(tmp_path, monkeypatch):
    from metachange_inform.metachange_inform import MetadataChangeInform

    config_path = _make_config(tmp_path)
    monkeypatch.setenv('DASHSCOPE_API_BASE', 'http://10.73.254.200:30000/v1')
    monkeypatch.setenv('LLM_MODEL', 'Qwen3-32B')
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'not-needed')

    inform = MetadataChangeInform(str(config_path))
    assert inform.config['llm']['base_url'] == 'http://10.73.254.200:30000/v1'
    assert inform.config['llm']['model_name'] == 'Qwen3-32B'
    assert inform.config['llm']['api_key'] == 'not-needed'


def test_excel_only_output_saves_xlsx_without_markdown(tmp_path):
    from metachange_inform.metachange_inform import MetadataChangeInform

    config_path = _make_config(tmp_path, "output:\n  format: excel\n  log_dir: ./logs\n  cache_dir: ./cache\n  report_dir: ./reports\n  filename_prefix: metadata_redundancy")
    inform = MetadataChangeInform(str(config_path))
    report_rows = [
        {
            'metadata_id': 'A1',
            'chinese_name': '主商户号',
            'data_type': 'String(64)',
            'opt_time': '2026-03-27 11:00:43',
            'opt_user': 'tester',
            'redundancy_status': '有冗余',
            'similarity_score': '0.880',
            'matched_metadata_id': 'B1',
            'matched_chinese_name': '商户主编号',
        }
    ]

    saved_path = inform.save_report('ignored markdown content', report_rows=report_rows)
    xlsx_path = Path(saved_path)
    md_peer = xlsx_path.with_suffix('.md')
    assert saved_path.endswith('.xlsx')
    assert not md_peer.exists()

    wb = load_workbook(saved_path)


def test_importing_module_without_pymysql_does_not_exit_process(monkeypatch):
    """Module import should not terminate the process when optional deps are missing."""
    import importlib
    import metachange_inform.metachange_inform as module

    monkeypatch.setattr(module, 'pymysql', None)
    inform_cls = getattr(module, 'MetadataChangeInform')
    assert inform_cls is not None

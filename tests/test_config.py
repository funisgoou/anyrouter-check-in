import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config import AppConfig, ProviderConfig, load_accounts_config


def test_default_providers_config():
	app_config = AppConfig.load_from_env()

	anyrouter = app_config.get_provider('anyrouter')
	agentrouter = app_config.get_provider('agentrouter')

	assert anyrouter is not None
	assert anyrouter.needs_waf_cookies() is True
	assert anyrouter.needs_manual_check_in() is True
	assert anyrouter.waf_cookie_names == ['acw_sc__v2', 'acw_tc', 'cdn_sec_tc']

	assert agentrouter is not None
	assert agentrouter.needs_waf_cookies() is False
	assert agentrouter.needs_manual_check_in() is False
	assert agentrouter.waf_cookie_names == []


def test_account_config_defaults(monkeypatch):
	monkeypatch.setenv(
		'ANYROUTER_ACCOUNTS',
		'[{"cookies":{"session":"abc"},"api_user":"12345"}]',
	)

	accounts = load_accounts_config()

	assert accounts is not None
	assert len(accounts) == 1
	assert accounts[0].provider == 'anyrouter'
	assert accounts[0].get_display_name(0) == 'Account 1'


def test_provider_from_dict_supports_agentrouter_without_waf():
	provider = ProviderConfig.from_dict(
		'agentrouter',
		{
			'domain': 'https://agentrouter.org',
			'sign_in_path': None,
			'bypass_method': None,
		},
	)

	assert provider.name == 'agentrouter'
	assert provider.needs_waf_cookies() is False
	assert provider.needs_manual_check_in() is False

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from checkin import check_in_account, get_user_info
from utils.config import AccountConfig, AppConfig


def test_get_user_info_reports_api_error():
	client = MagicMock()
	client.get.return_value.status_code = 200
	client.get.return_value.json.return_value = {'success': False, 'message': 'Not logged in'}

	result = get_user_info(client, {}, 'https://example.com/api/user/self')

	assert result == {'success': False, 'error': 'Failed to get user info: Not logged in'}


def test_get_user_info_reports_non_json_response():
	client = MagicMock()
	client.get.return_value.status_code = 200
	client.get.return_value.json.side_effect = json.JSONDecodeError('invalid JSON', '', 0)
	client.get.return_value.headers = {'content-type': 'text/html'}
	client.get.return_value.text = '<html> Access denied </html>'

	result = get_user_info(client, {}, 'https://example.com/api/user/self')

	assert result == {
		'success': False,
		'error': 'Failed to get user info: HTTP 200 returned non-JSON (text/html): <html> Access denied </html>',
	}


@pytest.mark.asyncio
async def test_missing_provider_returns_complete_result_tuple():
	account = AccountConfig(
		name='Unknown',
		provider='unknown',
		cookies={'session': 'test-session'},
		api_user='12345',
	)
	app_config = AppConfig.load_from_env()

	result = await check_in_account(account, 0, app_config)

	assert result == (False, None, None)


@pytest.mark.asyncio
async def test_cookie_preparation_failure_returns_complete_result_tuple():
	account = AccountConfig(
		name='AgentRouter',
		provider='agentrouter',
		cookies={'session': 'test-session'},
		api_user='12345',
	)
	app_config = AppConfig.load_from_env()

	with patch('checkin.prepare_cookies', new=AsyncMock(return_value=None)):
		result = await check_in_account(account, 0, app_config)

	assert result == (False, None, None)


@pytest.mark.asyncio
async def test_auto_check_in_fails_when_user_info_cannot_be_loaded():
	account = AccountConfig(
		name='AgentRouter',
		provider='agentrouter',
		cookies={'session': 'test-session'},
		api_user='12345',
	)
	app_config = AppConfig.load_from_env()
	client = MagicMock()

	with (
		patch('checkin.prepare_cookies', new=AsyncMock(return_value={'session': 'test-session'})),
		patch('checkin.httpx.Client', return_value=client),
		patch(
			'checkin.get_user_info',
			side_effect=[
				{'success': False, 'error': 'Failed to get user info: HTTP 401'},
				{'success': False, 'error': 'Failed to get user info: HTTP 401'},
				{'success': False, 'error': 'Failed to get user info: HTTP 401'},
			],
		),
		patch('checkin.asyncio.sleep', new=AsyncMock()),
	):
		success, before, after = await check_in_account(account, 0, app_config)

	assert success is False
	assert before['success'] is False
	assert after['success'] is False
	client.close.assert_called_once()


@pytest.mark.asyncio
async def test_auto_check_in_uses_initial_balance_when_refresh_fails():
	account = AccountConfig(
		name='AgentRouter',
		provider='agentrouter',
		cookies={'session': 'test-session'},
		api_user='12345',
	)
	app_config = AppConfig.load_from_env()
	client = MagicMock()
	initial_info = {'success': True, 'quota': 10.0, 'used_quota': 2.0, 'display': 'balance'}

	with (
		patch('checkin.prepare_cookies', new=AsyncMock(return_value={'session': 'test-session'})),
		patch('checkin.httpx.Client', return_value=client),
		patch(
			'checkin.get_user_info',
			side_effect=[
				initial_info,
				{'success': False, 'error': 'Temporary error'},
				{'success': False, 'error': 'Temporary error'},
			],
		),
		patch('checkin.asyncio.sleep', new=AsyncMock()),
	):
		success, before, after = await check_in_account(account, 0, app_config)

	assert success is True
	assert before == initial_info
	assert after == initial_info
	client.close.assert_called_once()

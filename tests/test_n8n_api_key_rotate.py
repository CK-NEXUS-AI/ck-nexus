import json
import stat
import urllib.error

from scripts import n8n_api_key_rotate as rotate_module


class Response:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, _limit): return json.dumps({'data': []}).encode()


def test_validate_key_sends_expected_header_and_accepts_workflow_list(monkeypatch):
    seen = {}
    def fake_open(req, timeout):
        seen['header'] = req.get_header('X-n8n-api-key')
        seen['url'] = req.full_url
        seen['timeout'] = timeout
        return Response()
    monkeypatch.setattr(rotate_module.urllib.request, 'urlopen', fake_open)
    assert rotate_module.validate_key('candidate-secret') == (True, 'verified')
    assert seen['header'] == 'candidate-secret'
    assert seen['url'].startswith('http://127.0.0.1:5678/')


def test_validate_key_rejects_401_without_exposing_body(monkeypatch):
    def fake_open(*args, **kwargs):
        raise urllib.error.HTTPError('local', 401, 'unauthorized', {}, None)
    monkeypatch.setattr(rotate_module.urllib.request, 'urlopen', fake_open)
    assert rotate_module.validate_key('bad-secret') == (False, 'http_401')


def test_rotate_validates_before_atomic_replace_and_keeps_backup(tmp_path, monkeypatch):
    path = tmp_path / 'api_key'
    path.write_text('old-key')
    path.chmod(0o600)
    monkeypatch.setattr(rotate_module.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(
        rotate_module,
        'validate_key',
        lambda key: (key == 'new-key', 'verified' if key == 'new-key' else 'http_401'),
    )
    ok, status = rotate_module.rotate(path, 'new-key')
    assert (ok, status) == (True, 'rotated_and_verified')
    assert path.read_text() == 'new-key'
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    backups = list(tmp_path.glob('api_key.backup-*'))
    assert len(backups) == 1
    assert backups[0].read_text() == 'old-key'
    assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600


def test_rotate_rejects_invalid_candidate_without_changing_file(tmp_path, monkeypatch):
    path = tmp_path / 'api_key'
    path.write_text('old-key')
    monkeypatch.setattr(rotate_module.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(rotate_module, 'validate_key', lambda key: (False, 'http_401'))
    assert rotate_module.rotate(path, 'bad-key') == (False, 'candidate_rejected_http_401')
    assert path.read_text() == 'old-key'
    assert not list(tmp_path.glob('api_key.backup-*'))


def test_validate_rejects_empty_and_control_characters():
    assert rotate_module.validate_key('') == (False, 'invalid_input')
    assert rotate_module.validate_key('bad\nkey') == (False, 'invalid_input')

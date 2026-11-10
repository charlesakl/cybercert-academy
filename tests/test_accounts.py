from datetime import date
from services.accounts import AccountClient, AccountError, SupabaseConfig, get_config
from services.progress import serialize, deserialize

class FakeResponse:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._payload = payload
        self.content = b'{}'
    def json(self):
        return self._payload

class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse(self.payload)


def test_config_rejects_insecure_urls():
    try:
        SupabaseConfig('http://example.com', 'anon')
        assert False
    except ValueError:
        pass


def test_config_from_secrets():
    cfg = get_config({'supabase': {'url': 'https://sample.supabase.co/', 'anon_key': 'public'}})
    assert cfg.url == 'https://sample.supabase.co'
    assert cfg.key == 'public'


def test_progress_round_trip():
    state = {'completed': {'D1-P05'}, 'current_lesson': 'D1-P05',
             'practice_history': [{'mode': 'mock', 'result': {'correct': 30, 'total': 50}}],
             'flashcard_reviews': {'F01': {'due': date(2026, 11, 12), 'step': 1}}}
    restored = deserialize(serialize(state))
    for key, value in state.items():
        assert restored[key] == value
    assert restored["activity_days"] == []
    assert restored["ai_daily_usage"] == {}


def test_user_scoped_reads_and_writes():
    transport = FakeTransport([{'payload': {'version': 1, 'completed': ['D1-P05']}}])
    client = AccountClient(SupabaseConfig('https://sample.supabase.co', 'public'), transport)
    data = client.load_progress('student-jwt', 'student-1')
    assert data['completed'] == ['D1-P05']
    method, url, opts = transport.calls[-1]
    assert opts['params']['user_id'] == 'eq.student-1'
    assert opts['headers']['Authorization'] == 'Bearer student-jwt'
    assert opts['headers']['apikey'] == 'public'
    client.save_progress('student-jwt', 'student-1', {'version': 1})
    method, url, opts = transport.calls[-1]
    assert method == 'POST' and 'on_conflict=user_id' in url
    assert opts['json']['user_id'] == 'student-1'
    assert opts['json']['payload'] == {'version': 1}


def test_server_errors_not_silently_ignored():
    class ErrorTransport(FakeTransport):
        def request(self, method, url, **kwargs):
            return FakeResponse({'message': 'Forbidden'}, 403)
    client = AccountClient(SupabaseConfig('https://sample.supabase.co', 'public'), ErrorTransport(None))
    try:
        client.load_progress('jwt', 'user')
        assert False
    except AccountError as exc:
        assert 'Forbidden' in str(exc)

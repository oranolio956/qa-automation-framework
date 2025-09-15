from automation.services.proxy_pool import ProxyPool


def test_proxy_pool_session_creation(monkeypatch):
    pool = ProxyPool(proxy_urls=["http://user:pass@127.0.0.1:8000"])  # dummy
    sess = pool.session()
    assert sess is not None
    assert 'http' in sess.proxies and 'https' in sess.proxies



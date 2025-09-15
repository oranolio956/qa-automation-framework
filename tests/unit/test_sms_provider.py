import os
import types

import pytest


class DummyMsg:
    def __init__(self, body: str):
        self.body = body


class DummyIncomingNumber:
    def __init__(self, phone_number: str):
        self.phone_number = phone_number


class DummyMessages:
    def __init__(self, bodies):
        self._bodies = bodies

    def list(self, to: str, limit: int = 20):
        return [DummyMsg(b) for b in self._bodies]


class DummyIncomingPhoneNumbers:
    def __init__(self, numbers):
        self._numbers = numbers

    def list(self, limit: int = 20, phone_number: str = None):
        if phone_number:
            return [DummyIncomingNumber(phone_number)]
        return [DummyIncomingNumber(n) for n in self._numbers]

    def create(self, phone_number: str):
        return types.SimpleNamespace(phone_number=phone_number, sid="PNXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

    def __call__(self, sid: str):
        class _Del:
            def delete(self):
                return True
        return _Del()


class DummyAvailable:
    def __init__(self, phone_number: str):
        self.phone_number = phone_number


class DummyCollection:
    def __init__(self, phone_number: str):
        self._pn = phone_number

    def list(self, limit=1, **kwargs):
        return [DummyAvailable(self._pn)]


class DummySearch:
    def __init__(self, phone_number: str):
        self.local = DummyCollection(phone_number)
        self.mobile = DummyCollection(phone_number)
        self.toll_free = DummyCollection(phone_number)


class DummyClient:
    def __init__(self, numbers, bodies, available_number: str = "+15559876543"):
        self.incoming_phone_numbers = DummyIncomingPhoneNumbers(numbers)
        self.messages = DummyMessages(bodies)
        self._available_number = available_number

    def available_phone_numbers(self, country: str):
        return DummySearch(self._available_number)


def test_twilio_provider_parses_code(monkeypatch):
    os.environ['TWILIO_ACCOUNT_SID'] = 'sid'
    os.environ['TWILIO_AUTH_TOKEN'] = 'token'

    import automation.services.sms_provider as sp

    # Monkeypatch Client used inside provider
    monkeypatch.setattr(sp, 'Client', lambda sid, tok: DummyClient(['+15551234567'], ['Your code is 123456']))

    provider = sp.TwilioSMSProvider()
    num = provider.get_number()
    assert num['success']
    code = provider.wait_for_code(num['phone_number'], timeout_seconds=1, poll_seconds=0)
    assert code == '123456'


def test_twilio_autopurchase(monkeypatch):
    os.environ['TWILIO_ACCOUNT_SID'] = 'sid'
    os.environ['TWILIO_AUTH_TOKEN'] = 'token'
    os.environ['TWILIO_AUTOBUY_ENABLED'] = 'true'
    os.environ['TWILIO_BUY_COUNTRY'] = 'US'
    os.environ['TWILIO_BUY_TYPE'] = 'local'
    os.environ['TWILIO_NUMBER_POOL'] = ''

    import automation.services.sms_provider as sp
    monkeypatch.setattr(sp, 'Client', lambda sid, tok: DummyClient([], []))

    provider = sp.TwilioSMSProvider()
    r = provider.get_number()
    assert r['success'] and r['message'] == 'autopurchased'
    # Ensure release tries to delete
    assert provider.release_number(r['phone_number']) is True



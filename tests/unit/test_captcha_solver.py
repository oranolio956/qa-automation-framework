import os
import types

import pytest


def test_get_captcha_solver_none_when_no_key(monkeypatch):
    os.environ.pop('TWOCAPTCHA_API_KEY', None)
    import importlib
    mod = importlib.import_module('automation.services.captcha_solver')
    importlib.reload(mod)
    solver = mod.get_captcha_solver()
    assert solver is None



from dxl.learn.model.base import *
from dxl.learn.config import config_with_name, clear_config
from doufo import identity


def test_residual_config_direct(clean_config):
    r = Residual('res', identity, 0.1)
    assert r.config[Residual.KEYS.CONFIG.RATIO] == 0.1


def test_residual_config_proxy(clean_config):
    c = config_with_name('res')
    c[Residual.KEYS.CONFIG.RATIO] = 0.1
    r = Residual('res', identity)
    assert r.config[Residual.KEYS.CONFIG.RATIO] == 0.1


def test_residual_config_default(clean_config):
    r = Residual('res', identity)
    assert r.config[Residual.KEYS.CONFIG.RATIO] == 0.3


def test_residual_config_proxy_direct_conflict(clean_config):
    c = config_with_name('res')
    c[Residual.KEYS.CONFIG.RATIO] = 0.1
    r = Residual('res', identity, 0.2)
    assert r.config[Residual.KEYS.CONFIG.RATIO] == 0.2
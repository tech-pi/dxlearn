import os
from pathlib import Path


def test_resource_path():
    return Path(os.getenv('HOME')) / 'share' / 'UnitTest' / 'dxlearn'

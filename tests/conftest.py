import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holdworld import anonbank as ab  # noqa: E402
from holdworld.helplines import all_helplines  # noqa: E402

needs_data = pytest.mark.skipif(not ab.available(), reason="real data not downloaded: python -m holdworld fetch-data")


@pytest.fixture(scope="session")
def calls():
    if not ab.available():
        pytest.skip("real data not downloaded")
    return ab.load()


@pytest.fixture(scope="session")
def summary(calls):
    return ab.summarize(calls)


@pytest.fixture(scope="session")
def model(calls):
    return ab.fit_model(calls)


@pytest.fixture(scope="session")
def helplines():
    return all_helplines()


@pytest.fixture
def rng():
    return random.Random(1234)

import pytest

from services.axonius_fixture import axonius_fixture
from services.ad_service import ad_fixture
from services.epo_service import epo_fixture


def test_system_is_up(axonius_fixture):
    print("system is up")


def test_ad_adapter_is_up(axonius_fixture, ad_fixture):
    print("system is up")


def test_epo_adapter_is_up(axonius_fixture, epo_fixture):
    print("epo fixture is up")

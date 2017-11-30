import pytest
from services.gui_service import gui_fixture


def test_adapter_is_up(axonius_fixture, gui_fixture):
    print("GUI is up")


def test_restart(axonius_fixture, gui_fixture):
    axonius_fixture.restart_plugin(gui_fixture)

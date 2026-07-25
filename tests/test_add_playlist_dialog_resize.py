"""Regression test: AddPlaylistDialog height must not grow after a YouTube→Local→YouTube tab switch."""
from __future__ import annotations

import sys
import pytest

from unittest.mock import MagicMock


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_dialog(qapp):
    state = MagicMock()
    state.playlists = []
    state._output_root = "/tmp"

    from ui.dialogs.add_playlist import AddPlaylistDialog
    dlg = AddPlaylistDialog(state, playlist=None)
    # show() triggers the initial layout pass so sizeHint is based on real geometry
    dlg.show()
    qapp.processEvents()
    dlg.adjustSize()
    qapp.processEvents()
    return dlg


def test_youtube_height_unchanged_after_local_roundtrip(qapp):
    dlg = _make_dialog(qapp)

    yt_height_before = dlg.height()
    assert yt_height_before > 0, "dialog must have a non-zero height"

    # switch to local folder
    dlg._on_source_changed("local")
    qapp.processEvents()
    local_height = dlg.height()
    assert local_height > yt_height_before, "local page must be taller than youtube page"

    # switch back to youtube
    dlg._on_source_changed("youtube")
    qapp.processEvents()
    yt_height_after = dlg.height()

    dlg.close()

    assert yt_height_after == yt_height_before, (
        f"dialog grew after local→youtube switch: "
        f"before={yt_height_before}px  local={local_height}px  after={yt_height_after}px"
    )

"""Pruebas de la aplicación: carga, acciones y render integrados sin monitor."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pytest.importorskip("pygame")

import pygame  # noqa: E402

from conftest import wait_until  # noqa: E402

from instinct.ui.app import App  # noqa: E402
from instinct.ui.controls import UIAction  # noqa: E402

GRASS = "terrain Grass\nchar .\nresource_max 100\nregen 2\n"
ROCK = "object Rock\nchar #\nresource_max 100\n"
MAP = "Prueba\n....\n.##.\n....\n"
URUK = """\
creature Uruk
faction isengard
health 80
vision 6
lifespan 400

start:
    wait(1)
    goto start
"""
BROKEN = """\
creature Roto
faction prueba
health 0
vision 3
lifespan 100

start:
    wait(1)
"""
BROKEN_DIAGNOSTIC = "Línea 3: health debe ser mayor que 0"


def build_content(tmp_path: Path) -> Path:
    """Crea el directorio base con contenido mínimo cargable."""
    for name, source in (
        ("terrains/grass.te", GRASS),
        ("objects/rock.ob", ROCK),
        ("maps/prueba.map", MAP),
        ("creatures/uruk.ins", URUK),
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return tmp_path


@pytest.fixture(autouse=True)
def _pygame_ready():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture()
def app(tmp_path: Path) -> App:
    return App(build_content(tmp_path), seed=42)


def start_simulation(app: App) -> None:
    """Lleva la aplicación de la carga a la simulación con una criatura."""
    app.session.load()
    app._execute(UIAction("map", "Prueba"))
    app._execute(UIAction("species", "Uruk"))
    app._execute(UIAction("cell", "0,0"))
    app._execute(UIAction("start"))


def test_load_fills_report_and_phase(app: App) -> None:
    app.session.load()
    assert app.session.state.phase == "map_select"
    assert "Prueba" in app.session.state.load_report


def test_map_action_renders_grid(app: App) -> None:
    app.session.load()
    app._execute(UIAction("map", "Prueba"))
    app.view.render(app.screen, app.session.state)
    assert app.session.state.phase == "placement"
    assert "grid" in app.view.hotspots
    assert app.session.state.camera_x > 0 or app.session.state.world is not None


def test_full_flow_reaches_simulation_and_steps(app: App) -> None:
    start_simulation(app)
    assert app.session.state.phase == "simulation"
    app._execute(UIAction("step"))
    assert app.session.state.tick == 1


def test_pause_action_toggles(app: App) -> None:
    start_simulation(app)
    app._execute(UIAction("pause"))
    assert app.session.state.paused is True
    app._execute(UIAction("pause"))
    assert app.session.state.paused is False


def test_speed_action_changes_tps(app: App) -> None:
    start_simulation(app)
    app._execute(UIAction("speed", "4"))
    assert app.session.state.speed_tps == 30


def test_speed_button_click_does_not_crash(app: App) -> None:
    start_simulation(app)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(10, 10), button=1)
    actions = app.controls.handle(event, {"speed": pygame.Rect(0, 0, 100, 30)})
    for action in actions:
        app._execute(action)
    assert app.session.state.speed_tps == 1
    for action in app.controls.handle(event, {"speed": pygame.Rect(0, 0, 100, 30)}):
        app._execute(action)
    assert app.session.state.speed_tps == 5


def test_repeat_action_replays_with_new_seed(app: App) -> None:
    start_simulation(app)
    app._execute(UIAction("step"))
    app.session.state.seed_input = "99"
    app._execute(UIAction("repeat"))
    assert app.session.state.seed == 99
    assert app.session.state.world.creature_at(0, 0) is not None
    assert app.session.state.tick == 0


def test_reset_action_returns_to_placement(app: App) -> None:
    start_simulation(app)
    app._execute(UIAction("step"))
    app._execute(UIAction("reset"))
    assert app.session.state.phase == "placement"
    assert app.session.state.tick == 0
    assert list(app.session.state.world.creatures()) == []


def test_quit_action_stops_the_loop(app: App) -> None:
    app._running = True
    app._execute(UIAction("quit"))
    assert app._running is False


def test_advance_simulation_steps_only_when_due(app: App) -> None:
    start_simulation(app)
    app.session.set_speed(0)  # 1 tps
    app._last_step = 0.0
    app._advance_simulation()
    assert app.session.state.tick == 1
    app._advance_simulation()  # aún no pasa el segundo
    assert app.session.state.tick == 1


def test_advance_simulation_skips_while_paused(app: App) -> None:
    start_simulation(app)
    app._execute(UIAction("pause"))
    app._last_step = 0.0
    app._advance_simulation()
    assert app.session.state.tick == 0


def test_editor_window_is_exported(qapp) -> None:
    """La ventana del editor se exporta de forma perezosa desde el paquete."""
    from PyQt6.QtWidgets import QMainWindow

    from instinct.ui.editor import EditorWindow

    assert issubclass(EditorWindow, QMainWindow)


def test_window_close_cancelled_stays_visible(
    app: App, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cerrar la ventana con Cancelar mantiene la ventana y el editor abiertos."""
    window = app._editor_window
    widget = app._editor_widget
    assert window is not None and widget is not None
    asked: list[bool] = []

    def _cancel() -> bool:
        asked.append(True)
        return False

    monkeypatch.setattr(widget, "confirm_close", _cancel, raising=False)
    window.show()
    qapp.processEvents()
    try:
        window.close()
        qapp.processEvents()
        assert asked == [True]
        assert window.isVisible() is True
        assert widget._tabs.count() == 1
    finally:
        window.hide()


def test_quit_action_cancelled_keeps_running(
    app: App, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La acción de salir no detiene el bucle si el editor cancela."""
    widget = app._editor_widget
    assert widget is not None
    asked: list[bool] = []

    def _cancel() -> bool:
        asked.append(True)
        return False

    monkeypatch.setattr(widget, "confirm_close", _cancel, raising=False)
    app._running = True

    app._execute(UIAction("quit"))

    assert asked == [True]
    assert app._running is True


def test_window_x_hides_without_shutdown_and_toggle_restores_lint(
    app: App, qapp, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La X confirmada oculta y reabrir reactiva el análisis de la pestaña."""
    window = app._editor_window
    widget = app._editor_widget
    assert window is not None and widget is not None
    source_path = tmp_path / "roto.ins"
    source_path.write_text(BROKEN, encoding="utf-8")
    widget._open_path(source_path)
    current = widget._current_editor()
    assert current is not None
    linter = current.property("_linter")
    assert linter is not None
    panel = lambda: [
        widget._error_list.item(i).text() for i in range(widget._error_list.count())
    ]
    assert wait_until(lambda: BROKEN_DIAGNOSTIC in panel())

    monkeypatch.setattr(widget, "confirm_close", lambda: True, raising=False)
    stopped: list[bool] = []
    monkeypatch.setattr(widget, "shutdown", lambda: stopped.append(True))
    window.show()
    qapp.processEvents()
    try:
        window.close()
        qapp.processEvents()
        assert window.isVisible() is False
        assert stopped == []
        assert linter._shutting_down is False

        widget._error_list.clear()
        app._toggle_editor_window()
        qapp.processEvents()
        assert window.isVisible() is True
        assert wait_until(lambda: BROKEN_DIAGNOSTIC in panel())
    finally:
        window.hide()


def test_window_close_cancelled_does_not_shutdown(
    app: App, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancelar la confirmación no apaga los recursos del editor."""
    window = app._editor_window
    widget = app._editor_widget
    assert window is not None and widget is not None
    monkeypatch.setattr(widget, "confirm_close", lambda: False, raising=False)
    stopped: list[bool] = []
    monkeypatch.setattr(widget, "shutdown", lambda: stopped.append(True))
    window.show()
    qapp.processEvents()
    try:
        window.close()
        qapp.processEvents()
        assert window.isVisible() is True
        assert stopped == []
    finally:
        window.hide()


def test_toggle_after_shutdown_does_not_reactivate_linters(
    app: App, qapp
) -> None:
    """Tras la salida real, reabrir la ventana no revive ningún linter."""
    window = app._editor_window
    widget = app._editor_widget
    assert window is not None and widget is not None
    current = widget._current_editor()
    assert current is not None
    linter = current.property("_linter")
    assert linter is not None

    app._shutdown_editor()
    assert linter._shutting_down is True
    assert linter._timer.isActive() is False

    app._toggle_editor_window()
    qapp.processEvents()
    assert window.isVisible() is True
    assert linter._shutting_down is True
    assert linter._timer.isActive() is False


def test_quit_event_asks_confirmation(
    app: App, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El evento QUIT de Pygame pasa por la misma confirmación que la acción."""
    widget = app._editor_widget
    assert widget is not None
    asked: list[bool] = []

    def _cancel() -> bool:
        asked.append(True)
        return False

    monkeypatch.setattr(widget, "confirm_close", _cancel, raising=False)

    polls: list[bool] = []

    def _fake_get():
        polls.append(True)
        if len(polls) == 1:
            return [pygame.event.Event(pygame.QUIT)]
        app._running = False
        return []

    monkeypatch.setattr(pygame.event, "get", _fake_get)
    monkeypatch.setattr(pygame, "quit", lambda: None)
    app._running = True

    app.run()

    assert asked == [True]


def test_quit_action_shuts_down_editor(
    app: App, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Al confirmar la salida se detienen los recursos del editor."""
    widget = app._editor_widget
    assert widget is not None
    stopped: list[bool] = []
    monkeypatch.setattr(widget, "shutdown", lambda: stopped.append(True))
    app._running = True

    app._execute(UIAction("quit"))

    assert stopped == [True]
    assert app._running is False

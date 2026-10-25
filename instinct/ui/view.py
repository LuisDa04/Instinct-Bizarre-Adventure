"""Renderizado de la interfaz: rejilla, paneles, registro y barra de estado."""
from __future__ import annotations

import pygame

from .assets import Assets
from .constants import (
    CHAR_HIDE_ZOOM,
    COLORS,
    HEALTH_BAR_BACKGROUND,
    HEALTH_BAR_BOTTOM_MARGIN,
    HEALTH_BAR_FULL,
    HEALTH_BAR_GOOD_RATIO,
    HEALTH_BAR_HEIGHT,
    HEALTH_BAR_INSET,
    HEALTH_BAR_WARNING_RATIO,
    LOG_HEIGHT,
    PANEL_WIDTH,
    PHASE_LOADING,
    PHASE_MAP_SELECT,
    PHASE_NO_MAPS,
    PHASE_PLACEMENT,
    STATUS_BAR_HEIGHT,
)
from .state import UIState

PHASE_LABELS = {
    PHASE_LOADING: "Cargando",
    PHASE_NO_MAPS: "Sin mapas",
    PHASE_MAP_SELECT: "Elección de mapa",
    PHASE_PLACEMENT: "Colocación",
    "simulation": "Simulación",
}


class View:
    """Dibuja un frame completo a partir del estado y expone los puntos interactivos.

    Tras cada render, `hotspots` guarda el rect de cada elemento clicable bajo
    una clave ("map:Nombre", "start", "grid", ...); los controles consultan esa
    tabla en el frame siguiente sin recalcular posiciones, así botón dibujado y
    botón clicable nunca se desincronizan.
    """

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.hotspots: dict[str, pygame.Rect] = {}
        self._previews: dict[str, pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Frame completo
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface, state: UIState) -> None:
        """Dibuja el frame acorde a la fase y llena la tabla de hotspots."""
        self.hotspots = {}
        screen.fill(COLORS["bg"])
        width, height = screen.get_size()
        panel = pygame.Rect(width - PANEL_WIDTH, 0, PANEL_WIDTH, height - STATUS_BAR_HEIGHT)
        grid = pygame.Rect(0, 0, width - PANEL_WIDTH, height - LOG_HEIGHT - STATUS_BAR_HEIGHT)
        logs = pygame.Rect(0, grid.height, width - PANEL_WIDTH, LOG_HEIGHT)

        if state.phase == PHASE_LOADING:
            self._render_loading(screen, state)
        elif state.phase == PHASE_NO_MAPS:
            self._render_no_maps(screen, state)
            self._render_panel(screen, panel, state)
        elif state.phase == PHASE_MAP_SELECT:
            self._render_report(screen, grid, state)
            self._render_panel(screen, panel, state)
        elif state.phase == PHASE_PLACEMENT:
            self._render_grid(screen, grid, state)
            self._render_logs(screen, logs, state)
            self._render_panel(screen, panel, state)
        else:
            self._render_grid(screen, grid, state)
            self._render_logs(screen, logs, state)
            self._render_panel(screen, panel, state)

        status = pygame.Rect(0, height - STATUS_BAR_HEIGHT, width, STATUS_BAR_HEIGHT)
        self._render_status(screen, status, state)

    # ------------------------------------------------------------------
    # Rejilla
    # ------------------------------------------------------------------

    def _render_grid(self, screen: pygame.Surface, rect: pygame.Rect, state: UIState) -> None:
        """Dibuja las celdas visibles con terreno, objeto y criatura en capas."""
        world = state.world
        if world is None:
            return
        tile_size = state.tile_size
        self.assets.ensure_tile_size(tile_size)
        origin_x = rect.x + state.camera_x
        origin_y = rect.y + state.camera_y
        start_x = max(0, -origin_x // tile_size)
        start_y = max(0, -origin_y // tile_size)
        end_x = min(world.width, start_x + rect.width // tile_size + 2)
        end_y = min(world.height, start_y + rect.height // tile_size + 2)

        hover = self._alpha_tile(COLORS["hover"])
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                cell = pygame.Rect(origin_x + x * tile_size, origin_y + y * tile_size, tile_size, tile_size)
                terrain = world.terrain_at(x, y)
                if terrain is not None:
                    screen.blit(self.assets.terrain_tile(terrain.name, (x + y) % 4), cell)
                    if terrain.char != " " and (
                        tile_size < CHAR_HIDE_ZOOM
                        or not self.assets.has_terrain_art(terrain.name)
                    ):
                        self._blit_char(screen, cell, terrain.char, (235, 235, 235))
                obj = world.object_at(x, y)
                if obj is not None:
                    screen.blit(self.assets.object_tile(obj.name), cell)
                    if (
                        tile_size < CHAR_HIDE_ZOOM
                        or not self.assets.has_object_art(obj.name)
                    ):
                        self._blit_char(screen, cell, obj.char, (20, 20, 25))
                creature = world.creature_at(x, y)
                if creature is not None:
                    screen.blit(self.assets.creature_token(creature.faction), cell)
                    self._blit_char(screen, cell, creature.name[0].upper(), (15, 15, 20))
                    self._draw_health_bar(screen, cell, creature.health)
                pygame.draw.rect(screen, COLORS["grid_line"], cell, 1)
                if state.hover_cell == (x, y):
                    screen.blit(hover, cell)
                if state.selected_cell == (x, y):
                    pygame.draw.rect(screen, COLORS["selection"], cell, 2)
        self.hotspots["grid"] = rect

    def _blit_char(self, screen: pygame.Surface, rect: pygame.Rect, char: str, color: tuple[int, int, int]) -> None:
        """Centra un carácter en la celda con la fuente de rejilla."""
        text = self.assets.font_mono.render(char, True, color)
        screen.blit(text, text.get_rect(center=rect.center))

    def _draw_health_bar(self, screen: pygame.Surface, rect: pygame.Rect, health: int) -> None:
        """Dibuja la barra de vida bajo la criatura; 100 cuenta como llena.

        La vida real no tiene tope: por encima de 100 la barra simplemente
        se queda llena, y los colores marcan el tramo (verde, ámbar, rojo).
        """
        bar = pygame.Rect(
            rect.x + HEALTH_BAR_INSET,
            rect.bottom - HEALTH_BAR_HEIGHT - HEALTH_BAR_BOTTOM_MARGIN,
            rect.width - HEALTH_BAR_INSET * 2,
            HEALTH_BAR_HEIGHT,
        )
        pygame.draw.rect(screen, HEALTH_BAR_BACKGROUND, bar)
        ratio = min(1.0, health / HEALTH_BAR_FULL)
        if ratio > 0:
            if ratio > HEALTH_BAR_GOOD_RATIO:
                color = COLORS["success"]
            elif ratio > HEALTH_BAR_WARNING_RATIO:
                color = COLORS["warning"]
            else:
                color = COLORS["danger"]
            fill = pygame.Rect(bar.x, bar.y, max(1, int(bar.width * ratio)), bar.height)
            pygame.draw.rect(screen, color, fill)

    def _alpha_tile(self, color: tuple[int, int, int, int]) -> pygame.Surface:
        """Crea la superficie translúcida del resaltado de hover."""
        surface = pygame.Surface((self.assets.tile_size, self.assets.tile_size), pygame.SRCALPHA)
        surface.fill(color)
        return surface

    # ------------------------------------------------------------------
    # Panel contextual
    # ------------------------------------------------------------------

    def _render_panel(self, screen: pygame.Surface, panel: pygame.Rect, state: UIState) -> None:
        """Dibuja el panel derecho según la fase actual."""
        pygame.draw.rect(screen, COLORS["panel_bg"], panel)
        pygame.draw.line(screen, COLORS["panel_border"], (panel.x, panel.y), (panel.x, panel.bottom), 2)
        y = panel.y + 12
        if state.phase == PHASE_NO_MAPS:
            y = self._title(screen, "SIN MAPAS VÁLIDOS", panel.x, y)
            self._lines(
                screen,
                ["Arregla los errores y", "vuelve a arrancar."],
                panel.x + 12, y + 8, COLORS["text"],
            )
            quit_rect = pygame.Rect(panel.x + 12, panel.bottom - 60, panel.width - 24, 40)
            self._button(screen, quit_rect, "SALIR", "quit", enabled=True)
        elif state.phase == PHASE_MAP_SELECT:
            y = self._title(screen, "MAPAS", panel.x, y)
            for name in state.map_names:
                item = pygame.Rect(panel.x + 12, y, panel.width - 24, 36)
                pygame.draw.rect(screen, COLORS["panel_border"], item, border_radius=6)
                text = self.assets.font_ui.render(name, True, COLORS["text"])
                screen.blit(text, (item.x + 10, item.y + 10))
                screen.blit(self._map_preview(state, name), (item.right - 58, item.y + 2))
                self.hotspots[f"map:{name}"] = item
                y += 44
        elif state.phase == PHASE_PLACEMENT:
            y = self._title(screen, "COLOCACIÓN", panel.x, y)
            y = self._lines(
                screen,
                ["Elige especie y clica una", "celda; clic sobre criatura la quita."],
                panel.x + 12, y + 4, COLORS["text_dim"],
            )
            for name in state.species_names:
                item = pygame.Rect(panel.x + 12, y, panel.width - 24, 30)
                active = state.placement_species == name
                bg = COLORS["accent"] if active else COLORS["panel_border"]
                pygame.draw.rect(screen, bg, item, border_radius=6)
                color = (10, 10, 15) if active else COLORS["text"]
                text = self.assets.font_ui.render(name, True, color)
                screen.blit(text, (item.x + 10, item.y + 7))
                self.hotspots[f"species:{name}"] = item
                y += 36
            y += 10
            has_creatures = state.world is not None and any(True for _ in state.world.creatures())
            start = pygame.Rect(panel.x + 12, y, panel.width - 24, 40)
            self._button(screen, start, "INICIAR", "start", enabled=has_creatures)
        else:
            y = self._title(screen, "SIMULACIÓN", panel.x, y)
            alive = 0
            if state.world is not None:
                alive = sum(1 for _ in state.world.creatures())
            hud = [
                f"Tick: {state.tick}",
                f"Velocidad: {state.speed_tps} tps (teclas 1-5)",
                f"Semilla: {state.seed}",
                f"Vivas: {alive}",
            ]
            for line in hud:
                y = self._lines(screen, [line], panel.x + 12, y, COLORS["text"])
            y += 6
            buttons = [
                ("PAUSA (Space)" if not state.paused else "SEGUIR (Space)", "pause"),
                ("PASO (S)", "step"),
                (f"VELOCIDAD: {state.speed_tps}", "speed"),
                ("REINICIAR (R)", "reset"),
                ("REPETIR CON SEMILLA", "repeat"),
            ]
            for label, key in buttons:
                item = pygame.Rect(panel.x + 12, y, panel.width - 24, 30)
                self._button(screen, item, label, key, enabled=True)
                y += 36
            y += 8
            label = self.assets.font_ui.render("Semilla:", True, COLORS["text_dim"])
            screen.blit(label, (panel.x + 12, y))
            y += 22
            seed_box = pygame.Rect(panel.x + 12, y, panel.width - 24, 28)
            pygame.draw.rect(screen, COLORS["bg"], seed_box, border_radius=4)
            border = COLORS["accent"] if state.seed_focused else COLORS["panel_border"]
            pygame.draw.rect(screen, border, seed_box, 2, border_radius=4)
            shown = state.seed_input + ("_" if state.seed_focused else "")
            text = self.assets.font_ui.render(shown, True, COLORS["text"])
            screen.blit(text, (seed_box.x + 8, seed_box.y + 6))
            self.hotspots["seed_input"] = seed_box
            self._lines(
                screen,
                ["Clic en el campo, escribe y", "Enter repite la partida."],
                panel.x + 12, seed_box.bottom + 8, COLORS["text_dim"],
            )

    # ------------------------------------------------------------------
    # Zonas de reporte, carga y registro
    # ------------------------------------------------------------------

    def _render_report(self, screen: pygame.Surface, rect: pygame.Rect, state: UIState) -> None:
        """Muestra el reporte de carga mientras se elige mapa."""
        self._title(screen, "ELIGE UN MAPA", rect.x + 12, rect.y + 12)
        self._lines(screen, state.load_report.splitlines(), rect.x + 12, rect.y + 48, COLORS["text_dim"])

    def _render_loading(self, screen: pygame.Surface, state: UIState) -> None:
        """Pantalla de carga con el reporte en cuanto existe."""
        width, height = screen.get_size()
        title = self.assets.font_ui.render("Cargando contenido...", True, COLORS["text"])
        screen.blit(title, title.get_rect(center=(width // 2, height // 2)))
        if state.load_report:
            self._lines(screen, state.load_report.splitlines(), 12, height // 2 + 30, COLORS["text_dim"])

    def _render_no_maps(self, screen: pygame.Surface, state: UIState) -> None:
        """Aviso de arranque sin mapas con el reporte de lo que falló."""
        self._title(screen, "SIN MAPAS VÁLIDOS", 12, 12)
        self._lines(screen, state.load_report.splitlines(), 12, 48, COLORS["text_dim"])

    def _render_logs(self, screen: pygame.Surface, rect: pygame.Rect, state: UIState) -> None:
        """Dibuja los últimos mensajes de la sesión que caben en el cuadro."""
        pygame.draw.rect(screen, COLORS["panel_bg"], rect)
        pygame.draw.line(screen, COLORS["panel_border"], (rect.x, rect.y), (rect.right, rect.y), 2)
        y = rect.y + 6
        line_height = self.assets.font_log.get_linesize()
        for line in state.messages[-(rect.height // line_height):]:
            color = COLORS["log_system"]
            if "dice:" in line:
                color = COLORS["log_say"]
            elif "ruge:" in line:
                color = COLORS["log_roar"]
            elif "línea" in line:
                color = COLORS["log_ictus"]
            text = self.assets.font_log.render(
                self._fit(line, rect.width - 16, self.assets.font_log), True, color
            )
            screen.blit(text, (rect.x + 8, y))
            y += line_height

    def _render_status(self, screen: pygame.Surface, rect: pygame.Rect, state: UIState) -> None:
        """Barra inferior con fase, mapa, medidas, zoom y celda bajo el ratón."""
        pygame.draw.rect(screen, COLORS["panel_bg"], rect)
        pygame.draw.line(screen, COLORS["panel_border"], (rect.x, rect.y), (rect.right, rect.y), 1)
        parts = [PHASE_LABELS.get(state.phase, state.phase)]
        if state.map_name is not None:
            parts.append(state.map_name)
        if state.world is not None:
            parts.append(f"{state.world.width}x{state.world.height}")
        parts.append(f"zoom {state.tile_size}px")
        if state.hover_cell is not None:
            parts.append(f"({state.hover_cell[0]}, {state.hover_cell[1]})")
        text = self.assets.font_ui.render("  |  ".join(parts), True, COLORS["text_dim"])
        screen.blit(text, (rect.x + 12, rect.y + 5))

    # ------------------------------------------------------------------
    # Helpers de dibujo
    # ------------------------------------------------------------------

    def _title(self, screen: pygame.Surface, text: str, x: int, y: int) -> int:
        """Escribe un título de sección y devuelve la Y siguiente."""
        surface = self.assets.font_ui.render(text, True, COLORS["accent"])
        screen.blit(surface, (x + 12, y))
        return y + 32

    def _lines(self, screen: pygame.Surface, lines: list[str], x: int, y: int, color: tuple[int, int, int]) -> int:
        """Escribe líneas seguidas y devuelve la Y tras la última."""
        for line in lines:
            surface = self.assets.font_ui.render(line, True, color)
            screen.blit(surface, (x, y))
            y += 20
        return y

    def _button(self, screen: pygame.Surface, rect: pygame.Rect, label: str, key: str, enabled: bool) -> None:
        """Dibuja un botón y registra su rect bajo la clave dada."""
        bg = COLORS["panel_border"] if enabled else COLORS["disabled"]
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        color = COLORS["text"] if enabled else COLORS["text_dim"]
        text = self.assets.font_ui.render(label, True, color)
        screen.blit(text, text.get_rect(center=rect.center))
        self.hotspots[key] = rect

    def _fit(self, text: str, width: int, font: pygame.font.Font) -> str:
        """Recorta el texto con puntos suspensivos hasta caber en el ancho."""
        while text and font.size(text)[0] > width:
            text = text[:-1]
        return text or ""

    def _map_preview(self, state: UIState, name: str) -> pygame.Surface:
        """Devuelve la miniatura del mapa, generada una sola vez."""
        if name in self._previews:
            return self._previews[name]
        game_map = state.loaded.maps[name]
        surface = pygame.Surface((52, 32))
        tile_w = 52 / game_map.width
        tile_h = 32 / game_map.height
        for y in range(game_map.height):
            for x in range(game_map.width):
                cell = game_map.cells[y][x]
                color = self.assets.terrain_color(cell.terrain.name)
                if cell.object is not None:
                    color = self.assets.object_color(cell.object.name)
                pygame.draw.rect(
                    surface,
                    color,
                    (int(x * tile_w), int(y * tile_h), max(1, int(tile_w) + 1), max(1, int(tile_h) + 1)),
                )
        self._previews[name] = surface
        return surface

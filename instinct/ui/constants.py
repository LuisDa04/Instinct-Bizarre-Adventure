"""Constantes de la interfaz gráfica: layout, colores y velocidades."""
from __future__ import annotations

# Reutiliza el catálogo del CLI para que ambas interfaces ofrezcan lo mismo.
from instinct.sim.cli import SPEEDS

# Ventana
WINDOW_TITLE = "Instinct Bizarre Adventure"
DEFAULT_WINDOW_SIZE = (1280, 800)
TARGET_FPS = 60

# Fases de la aplicación: la sesión avanza en este orden.
PHASE_LOADING = "loading"
PHASE_NO_MAPS = "no_maps"
PHASE_MAP_SELECT = "map_select"
PHASE_PLACEMENT = "placement"
PHASE_SIMULATION = "simulation"

# Rejilla
BASE_TILE_SIZE = 32
MIN_TILE_SIZE = 16
MAX_TILE_SIZE = 64
ZOOM_STEP = 4
CHAR_HIDE_ZOOM = 24

# Layout de paneles (píxeles)
PANEL_WIDTH = 300
LOG_HEIGHT = 180
STATUS_BAR_HEIGHT = 28

# Registro de mensajes
MAX_LOG_LINES = 200

# Paleta base de la interfaz
COLORS: dict[str, tuple[int, int, int]] = {
    "bg": (25, 25, 35),
    "panel_bg": (35, 35, 45),
    "panel_border": (60, 60, 80),
    "text": (230, 230, 240),
    "text_dim": (150, 150, 170),
    "accent": (0, 200, 255),
    "danger": (255, 80, 80),
    "success": (80, 255, 120),
    "warning": (255, 200, 0),
    "grid_line": (50, 50, 70),
    "hover": (255, 255, 255, 40),
    "selection": (0, 255, 255),
    "disabled": (70, 70, 85),
    "log_say": (100, 200, 255),
    "log_roar": (255, 180, 60),
    "log_ictus": (255, 80, 80),
    "log_system": (180, 180, 200),
}

# Barra de vida de las criaturas
HEALTH_BAR_FULL = 100
HEALTH_BAR_HEIGHT = 3
HEALTH_BAR_INSET = 3
HEALTH_BAR_BOTTOM_MARGIN = 2
HEALTH_BAR_BACKGROUND = (30, 30, 40)
HEALTH_BAR_GOOD_RATIO = 0.5
HEALTH_BAR_WARNING_RATIO = 0.25

# Un color por facción para distinguir criaturas de un vistazo.
FACTION_COLORS: dict[str, tuple[int, int, int]] = {
    "joestar": (0, 200, 255),
    "dio": (255, 50, 50),
    "hamon": (255, 215, 0),
}
FACTION_DEFAULT = (180, 180, 200)

# Colores de terreno y objeto por nombre; los desconocidos caen en gris.
TERRAIN_COLORS: dict[str, tuple[int, int, int]] = {
    "grass": (34, 139, 34),
    "morioh": (76, 164, 76),
    "adoquin": (110, 105, 118),
}
TERRAIN_DEFAULT = (70, 70, 80)

OBJECT_COLORS: dict[str, tuple[int, int, int]] = {
    "rock": (120, 120, 130),
    "steamroller": (206, 162, 54),
    "knives": (198, 198, 210),
}
OBJECT_DEFAULT = (160, 120, 60)

# Nombres con arte procedural propio; los desconocidos conservan su char.
GRASS_TERRAINS = frozenset({"grass", "morioh"})
COBBLESTONE_TERRAINS = frozenset({"adoquin"})
TERRAIN_ART = GRASS_TERRAINS | COBBLESTONE_TERRAINS
OBJECT_ART = frozenset({"steamroller", "knives"})

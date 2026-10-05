"""Original tiny 7-pixel endless runner frame source."""

from __future__ import annotations

from dataclasses import dataclass
import random

from .live import FrameSource
from .pixel_model import DEFAULT_HEIGHT, DEFAULT_WIDTH, PixelColor, PixelFrame


@dataclass
class Obstacle:
    x: float
    width: int
    height: int

    @property
    def left(self) -> int:
        return int(round(self.x))

    @property
    def right(self) -> int:
        return self.left + self.width - 1


class DinoRunnerSource(FrameSource):
    """Small original runner tuned for 90 x 7 BetaBrite-style displays."""

    width = DEFAULT_WIDTH
    height = DEFAULT_HEIGHT
    ground_y = 6
    player_x = 7
    player_width = 2
    player_height = 2

    def __init__(self, *, seed: int = 1, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        self.width = width
        self.height = height
        self.ground_y = height - 1
        self.random = random.Random(seed)
        self.seed = seed
        self.reset()

    def start(self) -> None:
        if self.game_over:
            self.reset()

    def reset(self) -> None:
        self.random.seed(self.seed)
        self.player_y = float(self.ground_y - self.player_height)
        self.velocity_y = 0.0
        self.on_ground = True
        self.running_tick = 0
        self.elapsed = 0.0
        self.score = 0
        self.speed = 10.0
        self.spawn_timer = 1.3
        self.obstacles: list[Obstacle] = []
        self.game_over = False
        self.collision = False

    def handle_input(self, action: str, pressed: bool = True) -> None:
        if not pressed:
            return
        if action in {"jump", "space", "up"}:
            self.jump()
        elif action == "restart":
            self.reset()

    def jump(self) -> None:
        if self.game_over:
            return
        if self.on_ground:
            self.velocity_y = -13.0
            self.on_ground = False

    def update(self, delta_seconds: float) -> None:
        if delta_seconds <= 0:
            return
        step = min(delta_seconds, 0.1)
        remaining = delta_seconds
        while remaining > 0:
            actual = min(step, remaining)
            self._update_step(actual)
            remaining -= actual

    def _update_step(self, delta_seconds: float) -> None:
        if self.game_over:
            return

        self.elapsed += delta_seconds
        self.running_tick += 1
        self.score = int(self.elapsed * 10)
        self.speed = min(22.0, 10.0 + self.elapsed * 0.55)

        gravity = 34.0
        self.velocity_y += gravity * delta_seconds
        self.player_y += self.velocity_y * delta_seconds
        floor_y = self.ground_y - self.player_height
        if self.player_y >= floor_y:
            self.player_y = float(floor_y)
            self.velocity_y = 0.0
            self.on_ground = True

        for obstacle in self.obstacles:
            obstacle.x -= self.speed * delta_seconds
        self.obstacles = [obstacle for obstacle in self.obstacles if obstacle.right >= 0]

        self.spawn_timer -= delta_seconds
        if self.spawn_timer <= 0:
            self._spawn_obstacle()

        self.collision = self._collides()
        if self.collision:
            self.game_over = True

    def _spawn_obstacle(self) -> None:
        width = self.random.choice([1, 1, 2])
        height = self.random.choice([1, 2])
        self.obstacles.append(Obstacle(float(self.width + self.random.randint(3, 9)), width, height))
        base_gap = max(0.75, 1.5 - self.elapsed * 0.02)
        self.spawn_timer = base_gap + self.random.random() * 0.8

    def _player_bounds(self) -> tuple[int, int, int, int]:
        left = self.player_x
        right = self.player_x + self.player_width - 1
        top = max(0, int(round(self.player_y)))
        bottom = min(self.ground_y - 1, top + self.player_height - 1)
        return left, top, right, bottom

    def _collides(self) -> bool:
        player_left, player_top, player_right, player_bottom = self._player_bounds()
        for obstacle in self.obstacles:
            obstacle_left = obstacle.left
            obstacle_right = obstacle.right
            obstacle_bottom = self.ground_y - 1
            obstacle_top = obstacle_bottom - obstacle.height + 1
            separated = (
                player_right < obstacle_left
                or player_left > obstacle_right
                or player_bottom < obstacle_top
                or player_top > obstacle_bottom
            )
            if not separated:
                return True
        return False

    def render(self) -> PixelFrame:
        frame = PixelFrame(width=self.width, height=self.height)
        for x in range(0, self.width, 2):
            frame.set_pixel(x, self.ground_y, PixelColor.DIM_GREEN)

        player_color = PixelColor.YELLOW if not self.game_over else PixelColor.RED
        left, top, right, bottom = self._player_bounds()
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                if 0 <= x < self.width and 0 <= y < self.height:
                    frame.set_pixel(x, y, player_color)
        if self.on_ground and not self.game_over:
            foot_x = left if self.running_tick % 2 else right
            if 0 <= foot_x < self.width:
                frame.set_pixel(foot_x, self.ground_y - 1, PixelColor.ORANGE)

        for obstacle in self.obstacles:
            bottom_y = self.ground_y - 1
            for x in range(obstacle.left, obstacle.left + obstacle.width):
                for y in range(bottom_y - obstacle.height + 1, bottom_y + 1):
                    if 0 <= x < self.width and 0 <= y < self.height:
                        frame.set_pixel(x, y, PixelColor.GREEN)

        self._draw_score(frame)
        return frame

    def _draw_score(self, frame: PixelFrame) -> None:
        markers = min(10, self.score // 10)
        start = max(0, self.width - 12)
        for offset in range(markers):
            x = start + offset
            if x < self.width:
                frame.set_pixel(x, 0, PixelColor.AMBER)


import unittest

from betabrite_controller.dino import DinoRunnerSource, Obstacle
from betabrite_controller.pixel_model import PixelColor


class DinoRunnerTests(unittest.TestCase):
    def test_initial_state_and_frame_dimensions(self):
        source = DinoRunnerSource(seed=42)
        frame = source.render()

        self.assertEqual((frame.width, frame.height), (90, 7))
        self.assertTrue(source.on_ground)
        self.assertFalse(source.game_over)
        self.assertEqual(source.score, 0)

    def test_jump_gravity_and_landing(self):
        source = DinoRunnerSource(seed=42)
        start_y = source.player_y

        source.handle_input("jump")
        source.update(0.1)
        self.assertLess(source.player_y, start_y)
        self.assertFalse(source.on_ground)

        for _ in range(30):
            source.update(0.05)
        self.assertTrue(source.on_ground)
        self.assertEqual(source.velocity_y, 0)

    def test_no_mid_air_infinite_jump(self):
        source = DinoRunnerSource(seed=42)
        source.jump()
        velocity = source.velocity_y
        source.jump()
        self.assertEqual(source.velocity_y, velocity)

    def test_obstacle_movement_spawn_and_score(self):
        source = DinoRunnerSource(seed=2)
        source.obstacles.append(Obstacle(30.0, 1, 1))
        source.update(0.5)
        self.assertLess(source.obstacles[0].x, 30.0)
        self.assertGreater(source.score, 0)

        source.spawn_timer = 0.01
        source.update(0.02)
        self.assertTrue(any(obstacle.x >= source.width for obstacle in source.obstacles))

    def test_collision_and_no_false_collision(self):
        source = DinoRunnerSource(seed=1)
        source.obstacles.append(Obstacle(float(source.player_x + 20), 1, 2))
        source.update(0.01)
        self.assertFalse(source.game_over)

        source.obstacles = [Obstacle(float(source.player_x), 1, 2)]
        source.update(0.01)
        self.assertTrue(source.game_over)
        self.assertTrue(source.collision)

    def test_restart_and_deterministic_rendering(self):
        first = DinoRunnerSource(seed=9)
        second = DinoRunnerSource(seed=9)
        for _ in range(20):
            first.update(0.05)
            second.update(0.05)
        self.assertEqual(first.render().to_rows(), second.render().to_rows())

        first.obstacles = [Obstacle(float(first.player_x), 1, 2)]
        first.update(0.01)
        self.assertTrue(first.game_over)
        first.handle_input("restart")
        self.assertFalse(first.game_over)
        self.assertEqual(first.score, 0)

    def test_render_never_writes_out_of_bounds(self):
        source = DinoRunnerSource(seed=5)
        source.obstacles = [Obstacle(-5.0, 3, 2), Obstacle(89.0, 3, 2)]
        frame = source.render()
        self.assertEqual(len(frame.pixels), 7)
        self.assertEqual(len(frame.pixels[0]), 90)
        self.assertIn(PixelColor.YELLOW, {pixel for row in frame.pixels for pixel in row})


if __name__ == "__main__":
    unittest.main()

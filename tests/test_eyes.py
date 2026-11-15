"""Testes de regressão para o ritmo dos olhos do Home."""
import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from home import EyesWidget


class EyeTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.eye = EyesWidget()
        self.eye.timer.stop()

    def tearDown(self):
        self.eye.close()

    def test_click_blink_has_cooldown(self):
        self.assertTrue(self.eye.blink_on_click(now=100))
        self.assertFalse(self.eye.blink_on_click(now=100.2))
        self.eye.blink_begin = -1
        self.assertFalse(self.eye.blink_on_click(now=100.9))
        self.assertTrue(self.eye.blink_on_click(now=101.5))

    def test_idle_look_does_not_change_before_scheduled_time(self):
        self.eye.follow_mouse = False
        self.eye.next_look = time.monotonic() + 10
        self.eye.target_gaze = 0.25
        self.eye.animate()
        self.assertEqual(self.eye.target_gaze, 0.25)

    def test_easing_moves_toward_target_without_jump(self):
        self.eye.follow_mouse = False
        self.eye.next_look = time.monotonic() + 10
        self.eye.gaze = 0.0
        self.eye.target_gaze = 0.45
        self.eye._last_frame = time.monotonic() - 0.05
        self.eye.animate()
        self.assertGreater(self.eye.gaze, 0.0)
        self.assertLess(self.eye.gaze, 0.10)


if __name__ == "__main__":
    unittest.main()

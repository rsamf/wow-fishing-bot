import cv2
import numpy as np
import pytest

from tests.synth_vision import icon_rgba, paste_icon, water_background
from wowfish.vision.calibrate import Calibration, calibrate_icon_scale
from wowfish.vision.template import load_icon_templates

TEMPLATES = load_icon_templates()


@pytest.mark.parametrize("side", [24, 40, 56, 96])
def test_calibration_recovers_the_icon_size_on_a_1080p_frame(side):
    frame = water_background(1920, 1080, np.random.default_rng(side))
    paste_icon(frame, icon_rgba(), side, 700, 400)
    cal = calibrate_icon_scale(frame, TEMPLATES)
    assert abs(cal.icon_size_px - side) <= 3
    assert abs(cal.x - 700) <= 3 and abs(cal.y - 400) <= 3
    assert cal.score >= 0.75


def test_calibration_on_a_5k_frame_is_within_three_pixels():
    frame = water_background(5120, 2880, np.random.default_rng(1))
    paste_icon(frame, icon_rgba(), 56, 2600, 1300)
    cal = calibrate_icon_scale(frame, TEMPLATES)
    assert abs(cal.icon_size_px - 56) <= 3 and cal.native_size == 79


def test_calibration_on_the_real_fixture():
    frame = cv2.imread("tests/fixtures/wow_icon_crop.png")
    cal = calibrate_icon_scale(frame, TEMPLATES)
    assert 50 <= cal.icon_size_px <= 62
    assert abs(cal.x - 512) <= 4 and abs(cal.y - 320) <= 4


def test_suggested_threshold_is_score_minus_ten_points_clamped():
    assert Calibration(56, 79, 0.92, 0, 0).suggested_threshold() == pytest.approx(0.82)
    assert Calibration(56, 79, 0.65, 0, 0).suggested_threshold() == pytest.approx(0.6)
    assert Calibration(56, 79, 1.0, 0, 0).suggested_threshold() == pytest.approx(0.9)

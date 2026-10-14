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


def test_a_gold_ring_in_the_ui_does_not_fool_calibration():
    """A unit-frame portrait ring scores ~0.8 for tiny templates; the real icon must still win."""
    frame = water_background(1920, 1080, np.random.default_rng(9))
    cv2.circle(frame, (60, 1020), 26, (40, 150, 215), thickness=7)  # gold ring, BGR
    cv2.circle(frame, (60, 1020), 16, (90, 120, 160), thickness=-1)  # a face-coloured centre
    paste_icon(frame, icon_rgba(), 40, 1000, 500)
    cal = calibrate_icon_scale(frame, TEMPLATES)
    assert abs(cal.icon_size_px - 40) <= 3
    assert abs(cal.x - 1000) <= 3 and abs(cal.y - 500) <= 3


SPIKE_FRAME = "superpowers/spike/wow_center.png"


@pytest.mark.skipif(not __import__("os").path.exists(SPIKE_FRAME), reason="local spike frame only")
def test_full_real_frame_with_ui_calibrates_to_the_icon():
    frame = cv2.imread(SPIKE_FRAME)  # 3072x1728 with the unit frame visible bottom-left
    cal = calibrate_icon_scale(frame, TEMPLATES)
    assert 52 <= cal.icon_size_px <= 60 and cal.native_size == 79
    assert abs(cal.x - 1575) <= 6 and abs(cal.y - 457) <= 6

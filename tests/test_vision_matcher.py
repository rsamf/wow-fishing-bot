import cv2
import numpy as np
import pytest

from tests.synth_vision import grey_icon_rgba, icon_rgba, paste_icon, water_background
from wowfish.vision.annotate import annotate_match
from wowfish.vision.matcher import GOLD_MIN, NO_MATCH, IconMatch, IconMatcher
from wowfish.vision.region import Region
from wowfish.vision.template import load_icon_templates, template_for_size

TEMPLATES = load_icon_templates()


def _frame(width, height, side, cx, cy, seed=0, brightness=1.0, rgba=None):
    rng = np.random.default_rng(seed)
    frame = water_background(width, height, rng)
    return paste_icon(frame, rgba if rgba is not None else icon_rgba(), side, cx, cy, brightness)


def test_finds_the_icon_at_native_resolution():
    frame = _frame(1920, 1080, 40, 600, 300)
    m = IconMatcher(template_for_size(TEMPLATES, 40)).match(frame)
    assert m.score >= 0.8 and m.gold >= GOLD_MIN
    assert abs(m.x - 600) <= 2 and abs(m.y - 300) <= 2 and m.size == 40


@pytest.mark.parametrize("seed", range(8))
def test_random_sizes_positions_and_brightness(seed):
    rng = np.random.default_rng(100 + seed)
    side = int(rng.integers(18, 110))
    cx = int(rng.integers(side, 1920 - side))
    cy = int(rng.integers(side, 1080 - side))
    frame = _frame(1920, 1080, side, cx, cy, seed=seed, brightness=float(rng.uniform(0.7, 1.3)))
    m = IconMatcher(template_for_size(TEMPLATES, side)).match(frame)
    assert m.score >= 0.75, (side, cx, cy, m)
    assert abs(m.x - cx) <= 3 and abs(m.y - cy) <= 3


@pytest.mark.parametrize(("cx", "cy"), [(30, 30), (1890, 30), (30, 1050), (1890, 1050)])
def test_icon_in_the_far_corners_is_found_by_a_whole_frame_match(cx, cy):
    frame = _frame(1920, 1080, 40, cx, cy)
    m = IconMatcher(template_for_size(TEMPLATES, 40)).match(frame)
    assert m.score >= 0.75 and abs(m.x - cx) <= 3 and abs(m.y - cy) <= 3


def test_5k_frame_is_downscaled_and_mapped_back():
    frame = _frame(5120, 2880, 56, 3000, 900)
    matcher = IconMatcher(template_for_size(TEMPLATES, 56), match_width=1920)
    m = matcher.match(frame)
    assert m.score >= 0.75
    assert abs(m.x - 3000) <= 6 and abs(m.y - 900) <= 6


def test_small_window_is_not_upscaled():
    frame = _frame(1280, 720, 30, 400, 200)
    m = IconMatcher(template_for_size(TEMPLATES, 30), match_width=1920).match(frame)
    assert m.score >= 0.75 and abs(m.x - 400) <= 2 and abs(m.y - 200) <= 2


def test_no_icon_scores_low():
    frame = water_background(1920, 1080, np.random.default_rng(5))
    m = IconMatcher(template_for_size(TEMPLATES, 40)).match(frame)
    assert m.score < 0.6


def test_grey_out_of_range_icon_fails_the_gold_gate():
    frame = _frame(1920, 1080, 40, 600, 300, rgba=grey_icon_rgba())
    m = IconMatcher(template_for_size(TEMPLATES, 40)).match(frame)
    assert m.gold < GOLD_MIN


def test_region_restricts_the_search_and_reports_frame_coordinates():
    frame = _frame(1920, 1080, 40, 600, 300)
    paste_icon(frame, icon_rgba(), 40, 1500, 800)
    matcher = IconMatcher(template_for_size(TEMPLATES, 40))
    right = matcher.match(frame, Region(0.6, 0.6, 1.0, 1.0))
    assert abs(right.x - 1500) <= 3 and abs(right.y - 800) <= 3
    tiny = matcher.match(frame, Region(0.0, 0.0, 0.005, 0.005))
    assert tiny.score == NO_MATCH


def test_real_fixture_crop():
    frame = cv2.imread("tests/fixtures/wow_icon_crop.png")
    m = IconMatcher(template_for_size(TEMPLATES, 56)).match(frame)
    assert m.score >= 0.85 and m.gold >= GOLD_MIN
    assert abs(m.x - 512) <= 4 and abs(m.y - 320) <= 4


def test_annotate_draws_a_box_on_a_thumbnail_of_the_matched_frame():
    frame = _frame(1920, 1080, 40, 600, 300)
    m = IconMatch(score=0.9, x=600, y=300, size=40, gold=0.3)
    thumb = annotate_match(frame, m, thumb_width=480)
    assert thumb.shape[1] == 480 and thumb.shape[0] == 270
    sx = 480 / 1920
    box = thumb[int(300 * sx) - 12 : int(300 * sx) + 12, int(600 * sx) - 12 : int(600 * sx) + 12]
    assert (box[:, :, 1] > 150).any()  # green rectangle pixels present
    untouched = annotate_match(frame, IconMatch(NO_MATCH, -1, -1, 40, 0.0), thumb_width=480)
    assert untouched.shape == thumb.shape


def test_template_below_the_match_space_floor_is_no_match():
    """At 5K a 19 px icon becomes a 7 px blob after downscaling to 1920 and matches anything."""
    from wowfish.vision.matcher import MIN_TEMPLATE_PX

    frame = _frame(4986, 2816, 19, 2432, 1482)
    tiny = IconMatcher(template_for_size(TEMPLATES, 19), match_width=1920)
    assert tiny.template_px(4986) < MIN_TEMPLATE_PX
    assert tiny.match(frame).score == NO_MATCH
    big = IconMatcher(template_for_size(TEMPLATES, 56), match_width=1920)
    assert big.template_px(4986) >= MIN_TEMPLATE_PX
    small = _frame(1920, 1080, 18, 700, 400)  # no downscale: 18 px is above the floor
    m = IconMatcher(template_for_size(TEMPLATES, 18), match_width=1920).match(small)
    assert m.score >= 0.75 and abs(m.x - 700) <= 2 and abs(m.y - 400) <= 2


def test_a_crop_matched_with_the_full_width_scores_like_the_full_frame():
    """Tracking grabs only a box; it must be scored at the same downscale as the acquire pass."""
    frame = _frame(4986, 2816, 56, 2600, 1300)
    matcher = IconMatcher(template_for_size(TEMPLATES, 56), match_width=1920)
    whole = matcher.match(frame)
    x0, y0 = 2600 - 400, 1300 - 250
    crop = frame[y0 : y0 + 500, x0 : x0 + 800]
    part = matcher.match(crop, full_width=4986)
    assert abs(part.score - whole.score) < 0.03
    assert abs(x0 + part.x - whole.x) <= 4 and abs(y0 + part.y - whole.y) <= 4
    native = matcher.match(crop)  # without the hint the 56 px template is used at native scale
    assert native.size == part.size and matcher.template_px(4986) < 30

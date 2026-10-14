import numpy as np

from tests.synth_vision import icon_rgba, paste_icon, water_background
from wowfish.vision.matcher import IconMatcher
from wowfish.vision.search import IconSearch
from wowfish.vision.template import load_icon_templates, template_for_size

TEMPLATES = load_icon_templates()


def _frame(cx=None, cy=None, seed=0):
    frame = water_background(1920, 1080, np.random.default_rng(seed))
    if cx is not None:
        paste_icon(frame, icon_rgba(), 40, cx, cy)
    return frame


def test_acquires_on_the_whole_frame_then_tracks_in_a_box():
    search = IconSearch(IconMatcher(template_for_size(TEMPLATES, 40)), threshold=0.75)
    assert search.phase == "acquire"
    phase, m = search.step(_frame(1500, 800))
    assert phase == "acquire" and m.accepted(0.75)
    assert search.phase == "track"
    assert search.region is not None and search.region.to_box(1920, 1080)[0] > 1000
    phase, m = search.step(_frame(1505, 803))
    assert phase == "track" and abs(m.x - 1505) <= 3


def test_loses_the_track_after_three_misses_and_reacquires_elsewhere():
    matcher = IconMatcher(template_for_size(TEMPLATES, 40))
    search = IconSearch(matcher, threshold=0.75, lost_after=3)
    search.step(_frame(1500, 800))
    for _ in range(3):
        phase, m = search.step(_frame(200, 200))  # icon jumped far outside the tracking box
        assert phase == "track" and not m.accepted(0.75)
    assert search.phase == "acquire"
    phase, m = search.step(_frame(200, 200))
    assert phase == "acquire" and abs(m.x - 200) <= 3 and search.phase == "track"


def test_reset_returns_to_acquire():
    search = IconSearch(IconMatcher(template_for_size(TEMPLATES, 40)), threshold=0.75)
    search.step(_frame(900, 500))
    search.reset()
    assert search.phase == "acquire" and search.region is None

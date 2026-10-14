import pytest

from wowfish.vision.region import FULL, Region


def test_full_region_maps_to_the_whole_frame():
    assert FULL.to_box(1920, 1080) == (0, 0, 1920, 1080)


def test_to_box_rounds_and_never_returns_an_empty_box():
    assert Region(0.25, 0.5, 0.75, 1.0).to_box(100, 10) == (25, 5, 75, 10)
    x0, y0, x1, y1 = Region(0.0, 0.0, 0.001, 0.001).to_box(100, 100)
    assert x1 > x0 and y1 > y0


@pytest.mark.parametrize(
    "bad", [(0.5, 0.0, 0.5, 1.0), (-0.1, 0, 1, 1), (0, 0, 1, 1.2), (0.6, 0, 0.4, 1)]
)
def test_invalid_regions_are_rejected(bad):
    with pytest.raises(ValueError):
        Region(*bad)


def test_around_centres_a_box_on_the_point():
    r = Region.around(960, 540, 1920, 1080, margin=0.10)
    assert (r.left, r.top, r.right, r.bottom) == pytest.approx((0.4, 0.4, 0.6, 0.6))


@pytest.mark.parametrize(("x", "y"), [(0, 0), (1919, 0), (0, 1079), (1919, 1079)])
def test_around_clamps_at_the_corners(x, y):
    r = Region.around(x, y, 1920, 1080, margin=0.10)
    assert 0.0 <= r.left < r.right <= 1.0 and 0.0 <= r.top < r.bottom <= 1.0
    x0, y0, x1, y1 = r.to_box(1920, 1080)
    assert x0 <= x < x1
    assert y0 <= y < y1

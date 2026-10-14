import numpy as np
import pytest

from wowfish.vision.template import (
    IconTemplate,
    load_icon_templates,
    resize_template,
    template_for_size,
)


@pytest.fixture(scope="module")
def templates():
    return load_icon_templates()


def test_loads_five_square_templates_with_binary_masks(templates):
    assert [t.native_size for t in templates] == [29, 42, 53, 79, 103]
    for t in templates:
        assert t.size == t.native_size
        assert t.bgr.shape == (t.size, t.size, 3) and t.bgr.dtype == np.uint8
        assert t.mask.shape == (t.size, t.size) and set(np.unique(t.mask)) <= {0, 255}
        opaque = (t.mask > 0).mean()
        assert 0.4 < opaque < 0.9, opaque


def test_resize_down_and_up_keeps_mask_binary(templates):
    t79 = templates[3]
    small = resize_template(t79, 56)
    assert small.size == 56 and small.native_size == 79
    assert small.bgr.shape == (56, 56, 3) and set(np.unique(small.mask)) <= {0, 255}
    big = resize_template(t79, 90)
    assert big.size == 90
    assert resize_template(t79, 79) is t79


@pytest.mark.parametrize(("size", "native"), [(20, 29), (29, 29), (56, 79), (103, 103), (140, 103)])
def test_template_for_size_prefers_the_smallest_native_at_least_as_big(templates, size, native):
    t = template_for_size(templates, size)
    assert isinstance(t, IconTemplate)
    assert (t.native_size, t.size) == (native, size)

"""SDR ~1 on a seamless tile, well above 1 on a broken one. Run: python tests/test_sdr.py"""
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent.parent))
from chhaap.metrics import sdr, wrap_error  # noqa: E402


def test_sdr():
    rng = np.random.default_rng(0)
    seamless = ndimage.gaussian_filter(rng.random((256, 256)), 3, mode="wrap") * 255
    broken = np.roll(seamless, 57, axis=1) + np.linspace(0, 40, 256)[None, :]  # ramp breaks the wrap
    s_ok, s_bad = sdr(seamless), sdr(broken)
    assert 0.8 < s_ok < 1.25, s_ok
    assert s_bad > 1.5, s_bad
    assert wrap_error(seamless) < 2 < wrap_error(broken)
    print(f"seamless SDR={s_ok:.3f} wrap={wrap_error(seamless):.2f}  broken SDR={s_bad:.3f} wrap={wrap_error(broken):.2f}")


if __name__ == "__main__":
    test_sdr()

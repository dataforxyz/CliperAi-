#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test: logo_scale is applied in filter_complex.

Verifica que el filtergraph de overlay del logo incluya un scale2ref relativo
al ancho del video (main_w * logo_scale).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_logo_scale_applied():
    from src.video_exporter import VideoExporter

    exporter = VideoExporter.__new__(VideoExporter)  # evita __init__ (ffmpeg check)
    chains, out = exporter._get_logo_overlay_filter(
        video_stream="[0:v]",
        logo_stream="[1:v]",
        position="top-right",
        scale=0.25,
    )

    assert any("scale2ref" in c for c in chains), "Expected scale2ref in logo filtergraph"
    assert any("main_w*0.25" in c for c in chains), "Expected logo_scale applied via main_w*scale"
    assert out == "[v_out]"


if __name__ == "__main__":
    test_logo_scale_applied()
    print("✓ PASS: logo_scale is applied in filter_complex filtergraph")

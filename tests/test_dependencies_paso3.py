#!/usr/bin/env python3
"""
Test: Verificar instalación de dependencias PASO3
Valida que OpenCV y MediaPipe estén correctamente instalados
"""

import sys


def test_opencv():
    import cv2

    print(f"✓ OpenCV installed: {cv2.__version__}")
    assert cv2.__version__ is not None


def test_mediapipe():
    import mediapipe as mp

    print(f"✓ MediaPipe installed: {mp.__version__}")
    assert mp.__version__ is not None

    # Test face detection model loading
    face_detection = mp.solutions.face_detection
    detector = face_detection.FaceDetection(min_detection_confidence=0.5)
    print("✓ MediaPipe face detection model loaded")
    assert detector is not None
    detector.close()


if __name__ == "__main__":
    print("Testing PASO3 dependencies...\n")

    try:
        test_opencv()
        test_mediapipe()
        print("\n" + "=" * 50)
        print("✓ All dependencies working!")
        sys.exit(0)
    except (ImportError, AssertionError) as e:
        print("\n" + "=" * 50)
        print(f"✗ Some dependencies failed: {e}")
        sys.exit(1)

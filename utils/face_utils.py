import cv2
import numpy as np
import mediapipe as mp
import os
from PIL import Image


class FaceAnalyzer:
    """Face shape detection using MediaPipe Face Mesh and landmark analysis."""

    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

    def detect_face(self, image_path):
        """Detect face and return face landmarks."""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_image)
        return results, image

    def get_face_measurements(self, landmarks, image_shape):
        """Calculate face measurements from landmarks."""
        h, w = image_shape[:2]

        def get_point(idx):
            return (int(landmarks[idx].x * w), int(landmarks[idx].y * h))

        # Key landmarks for face shape detection
        # Forehead top - landmark 10
        forehead = get_point(10)
        # Chin bottom - landmark 152
        chin = get_point(152)
        # Left cheek - landmark 234
        left_cheek = get_point(234)
        # Right cheek - landmark 454
        right_cheek = get_point(454)
        # Left jaw - landmark 172
        left_jaw = get_point(172)
        # Right jaw - landmark 397
        right_jaw = get_point(397)
        # Left forehead - landmark 54
        left_forehead = get_point(54)
        # Right forehead - landmark 284
        right_forehead = get_point(284)

        # Calculate distances
        face_height = abs(chin[1] - forehead[1])
        face_width_cheek = abs(right_cheek[0] - left_cheek[0])
        jaw_width = abs(right_jaw[0] - left_jaw[0])
        forehead_width = abs(right_forehead[0] - left_forehead[0])

        return {
            'face_height': face_height,
            'cheek_width': face_width_cheek,
            'jaw_width': jaw_width,
            'forehead_width': forehead_width,
            'forehead': forehead,
            'chin': chin,
            'left_cheek': left_cheek,
            'right_cheek': right_cheek
        }

    def classify_face_shape(self, measurements):
        """Classify face shape based on measurements."""
        h = measurements['face_height']
        cw = measurements['cheek_width']
        jw = measurements['jaw_width']
        fw = measurements['forehead_width']

        if h == 0 or cw == 0:
            return 'oval'

        ratio = h / cw
        jaw_to_cheek = jw / cw if cw > 0 else 0
        fore_to_cheek = fw / cw if cw > 0 else 0

        # Classification logic based on facial proportion guidelines
        
        # 1. Very long face
        if ratio > 1.45:
            return 'oblong'
            
        # 2. Very round face (width ≈ height, soft jaw)
        if ratio < 1.15 and jaw_to_cheek > 0.75 and fore_to_cheek > 0.75:
            return 'round'
            
        # 3. Square (wide forehead & jaw, similar to cheek width)
        if jaw_to_cheek > 0.88 and fore_to_cheek > 0.85:
            return 'square'
            
        # 4. Triangle (jaw is noticeably wider than forehead)
        # Note: the user mentioned "female type in tringal"
        if jaw_to_cheek > 0.88 and fore_to_cheek < 0.85:
            return 'triangle'
            
        # 5. Heart/Inverted Triangle (wide forehead, narrow delicate jaw)
        if fore_to_cheek > 0.85 and jaw_to_cheek < 0.82:
            return 'heart'
            
        # 6. Diamond (narrow forehead & narrow jaw, wide cheeks)
        if fore_to_cheek < 0.85 and jaw_to_cheek < 0.85:
            return 'diamond'

        # Default fallback if nothing strongly triggers
        return 'oval'

    def analyze(self, image_path):
        """Main analysis function - returns face shape and measurements."""
        try:
            results, image = self.detect_face(image_path)

            if not results.multi_face_landmarks:
                return {
                    'success': False,
                    'error': 'No human face detected. Please upload a clear front-facing photo of a person.',
                    'face_shape': None
                }

            landmarks = results.multi_face_landmarks[0].landmark
            measurements = self.get_face_measurements(landmarks, image.shape)

            # ── Minimum face size guard ────────────────────────────────────
            # A real human face photo should produce a face height >= 80px.
            # Values below this indicate an animal, tiny thumbnail, or cartoon.
            MIN_FACE_HEIGHT = 80
            MIN_FACE_WIDTH  = 60
            if (measurements['face_height'] < MIN_FACE_HEIGHT or
                    measurements['cheek_width'] < MIN_FACE_WIDTH):
                return {
                    'success': False,
                    'error': (
                        f"No human face detected (face region too small: "
                        f"{measurements['face_height']}×{measurements['cheek_width']}px). "
                        "Please upload a clear, close-up front-facing photo of a person."
                    ),
                    'face_shape': None
                }
            # ──────────────────────────────────────────────────────────────

            face_shape = self.classify_face_shape(measurements)

            return {
                'success': True,
                'face_shape': face_shape,
                'measurements': {
                    'face_height': measurements['face_height'],
                    'cheek_width': measurements['cheek_width'],
                    'jaw_width': measurements['jaw_width'],
                    'forehead_width': measurements['forehead_width']
                },
                'landmarks': {
                    'forehead': measurements['forehead'],
                    'chin': measurements['chin'],
                    'left_cheek': measurements['left_cheek'],
                    'right_cheek': measurements['right_cheek'],
                    'left_jaw': (int(landmarks[172].x * image.shape[1]),
                                 int(landmarks[172].y * image.shape[0])),
                    'right_jaw': (int(landmarks[397].x * image.shape[1]),
                                 int(landmarks[397].y * image.shape[0])),
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'face_shape': None
            }


# Singleton instance
face_analyzer = FaceAnalyzer()

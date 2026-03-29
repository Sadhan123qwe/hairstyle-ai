import json
import os


class StyleRecommender:
    """Recommends hairstyles and beard styles based on face shape and gender."""

    def __init__(self):
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'styles.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            self.styles_data = json.load(f)

    def get_recommendations(self, face_shape, gender='male'):
        """Get style recommendations for a given face shape and gender."""
        face_shape = face_shape.lower()
        gender = gender.lower()

        if face_shape not in self.styles_data:
            face_shape = 'oval'  # Default fallback

        shape_data = self.styles_data[face_shape]

        # Get hairstyles based on gender
        if gender in shape_data.get('hairstyles', {}):
            hairstyles = shape_data['hairstyles'][gender]
        else:
            hairstyles = shape_data['hairstyles'].get('male', [])

        # Beard styles (primarily for males but included for all)
        beard_styles = shape_data.get('beard_styles', [])

        return {
            'face_shape': face_shape,
            'description': shape_data.get('description', ''),
            'hairstyles': hairstyles,
            'beard_styles': beard_styles if gender == 'male' else [],
            'total_hairstyles': len(hairstyles),
            'total_beard_styles': len(beard_styles) if gender == 'male' else 0
        }

    def get_all_face_shapes(self):
        """Return list of all supported face shapes."""
        return list(self.styles_data.keys())

    def get_face_shape_info(self, face_shape):
        """Get description for a specific face shape."""
        if face_shape in self.styles_data:
            return self.styles_data[face_shape].get('description', '')
        return ''


# Singleton instance
style_recommender = StyleRecommender()

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.utils import secure_filename
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from database import get_db
import os
import uuid
import datetime

analysis_bp = Blueprint('analysis', __name__)


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def login_required_route(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this feature.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def init_analysis():
    """Initialize analysis routes."""

    @analysis_bp.route('/analyze', methods=['GET', 'POST'])
    @login_required_route
    def analyze():
        if request.method == 'POST':
            from utils.face_utils import face_analyzer
            from utils.style_recommender import style_recommender
            from utils.gender_detector import detect_gender

            if 'image' not in request.files:
                flash('No image file uploaded.', 'error')
                return render_template('analysis.html')

            file = request.files['image']

            if file.filename == '':
                flash('No file selected.', 'error')
                return render_template('analysis.html')

            allowed_ext = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg'})
            if not allowed_file(file.filename, allowed_ext):
                flash('Unsupported file type. Please upload PNG, JPG, or JPEG.', 'error')
                return render_template('analysis.html')

            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)

            ext = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(upload_folder, unique_filename)
            file.save(filepath)

            # ── Auto-detect gender via Gemini Flash Lite ──────────────────
            gender_source = 'ai_detected'
            try:
                detected_gender = detect_gender(filepath)
                gender = detected_gender
                print(f"[INFO] AI gender detection success: {gender}")
            except Exception as e:
                gender = 'male'
                gender_source = 'ai_failed_default'
                print(f"[WARN] AI gender detection failed ({e}), defaulting to: {gender}")

            analysis_result = face_analyzer.analyze(filepath)

            if not analysis_result['success']:
                if os.path.exists(filepath):
                    os.remove(filepath)
                flash('⚠️ ' + analysis_result['error'], 'error')
                return render_template('analysis.html')

            face_shape = analysis_result['face_shape']
            recommendations = style_recommender.get_recommendations(face_shape, gender)

            hair_previews = []
            beard_previews = []

            # Save to history
            try:
                current_db = get_db()
                if current_db is not None:
                    current_db.analysis_history.insert_one({
                        'user_id': session['user_id'],
                        'username': session['username'],
                        'image_filename': unique_filename,
                        'face_shape': face_shape,
                        'gender': gender,
                        'gender_source': 'ai_detected',
                        'measurements': analysis_result.get('measurements', {}),
                        'analyzed_at': datetime.datetime.utcnow()
                    })
            except Exception as e:
                print(f"[WARNING] Could not save history: {e}")

            # ── Store result in session then redirect to GET /result ──────────
            # This gives the result page a stable, bookmarkable URL so the
            # AR Try-On Close button can navigate back to it correctly.
            session['last_result'] = {
                'face_shape':      face_shape,
                'gender':          gender,
                'recommendations': {
                    'description':   recommendations.get('description', ''),
                    'hairstyles':    recommendations.get('hairstyles', []),
                    'beard_styles':  recommendations.get('beard_styles', []),
                },
                'image_filename':  unique_filename,
                'measurements':    analysis_result.get('measurements', {}),
            }
            return redirect(url_for('analysis.result'))

        return render_template('analysis.html')

    @analysis_bp.route('/result')
    @login_required_route
    def result():
        """Show the last analysis result stored in session."""
        data = session.get('last_result')
        if not data:
            flash('No analysis result found. Please upload a photo.', 'warning')
            return redirect(url_for('analysis.analyze'))
        return render_template(
            'result.html',
            face_shape      = data['face_shape'],
            gender          = data['gender'],
            gender_detected = True,
            recommendations = data['recommendations'],
            image_filename  = data['image_filename'],
            measurements    = data.get('measurements', {}),
            hair_previews   = [],
            beard_previews  = [],
        )

    @analysis_bp.route('/history')
    @login_required_route
    def history():
        history_items = []
        try:
            current_db = get_db()
            if current_db is not None:
                history_items = list(current_db.analysis_history.find(
                    {'user_id': session['user_id']}
                ).sort('analyzed_at', -1).limit(20))
                for item in history_items:
                    item['_id'] = str(item['_id'])
        except Exception as e:
            flash('Could not load history.', 'warning')
        return render_template('history.html', history_items=history_items)

    @analysis_bp.route('/api/face-shapes')
    def get_face_shapes():
        from utils.style_recommender import style_recommender
        return jsonify({'face_shapes': style_recommender.get_all_face_shapes()})

    @analysis_bp.route('/try-on')
    @login_required_route
    def try_on():
        style_name = request.args.get('style', 'Unknown Style')
        style_type = request.args.get('type',  'hairstyle')
        return render_template('filter.html',
                               style_name=style_name,
                               style_type=style_type)

    @analysis_bp.route('/api/ar-snapshot', methods=['POST'])
    @login_required_route
    def ar_snapshot():
        """
        Receive a webcam frame (base64 JPEG) + style name/type.
        Pipeline:
          1. Replicate stable-diffusion-inpainting  (photo-realistic)
          2. Replicate SDXL img2img                 (fallback AI)
          3. OpenCV 3D renderer                     (always-working fallback)
        Returns JSON { image: 'data:image/jpeg;base64,...', source: '...' }
        """
        import base64
        import numpy as np

        gen_pil   = None   # track whether Replicate succeeded
        tmp_path  = None
        mask_path = None

        try:
            data       = request.get_json(force=True)
            img_b64    = data.get('image', '')
            style_name = data.get('style', 'Default')
            style_type = data.get('type',  'hairstyle')

            if not img_b64:
                return jsonify({'error': 'No image provided'}), 400

            # ── Decode base64 JPEG frame ──────────────────────────────────────
            img_bytes = base64.b64decode(img_b64.split(',')[-1])
            np_arr    = np.frombuffer(img_bytes, np.uint8)

            import cv2
            img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img_bgr is None:
                return jsonify({'error': 'Could not decode image'}), 400

            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            snap_id   = uuid.uuid4().hex
            tmp_path  = os.path.join(upload_folder, f'ar_snap_{snap_id}.jpg')
            mask_path = os.path.join(upload_folder, f'ar_mask_{snap_id}.png')
            cv2.imwrite(tmp_path, img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # ── Face landmarks ────────────────────────────────────────────────
            from utils.face_utils import face_analyzer
            analysis = face_analyzer.analyze(tmp_path)
            lm = analysis.get('landmarks', {})
            if not lm:
                h_i, w_i = img_bgr.shape[:2]
                lm = {
                    'forehead':    (w_i//2, h_i//5),
                    'left_cheek':  (w_i//4, h_i//2),
                    'right_cheek': (3*w_i//4, h_i//2),
                    'left_jaw':    (w_i//4, 3*h_i//4),
                    'right_jaw':   (3*w_i//4, 3*h_i//4),
                    'chin':        (w_i//2, 4*h_i//5),
                }

            # ── Style helpers ─────────────────────────────────────────────────
            from utils.style_preview import (
                _find, _opencv_render, _build_mask, _save_mask_image,
                _replicate_generate, _apply_cinematic_yellow_tint,
                HAIR_MASKS, HAIR_CFG, BEARD_MASKS, BEARD_CFG,
                _s_hair_generic, _s_beard_full,
            )

            is_beard = (style_type == 'beard')
            MASKS    = BEARD_MASKS if is_beard else HAIR_MASKS
            CFGS     = BEARD_CFG   if is_beard else HAIR_CFG

            mask_fn = _find(style_name, MASKS) or (
                _s_beard_full if is_beard else
                (lambda d, l, w, h: _s_hair_generic(d, l, w, h, 0))
            )
            cfg = _find(style_name, CFGS) or (
                BEARD_CFG['_default'] if is_beard else HAIR_CFG['_default']
            )

            result_bgr = None

            # ── 1. Replicate (inpainting → SDXL) ─────────────────────────────
            try:
                h_i, w_i = img_bgr.shape[:2]
                mask_np  = _build_mask(mask_fn, lm, w_i, h_i, blur_r=18)
                _save_mask_image(mask_np, mask_path)

                api_type = 'beard' if is_beard else 'hair'
                gen_pil  = _replicate_generate(tmp_path, mask_path, style_name, api_type)
                if gen_pil is not None:
                    gen_bgr    = cv2.cvtColor(np.array(gen_pil), cv2.COLOR_RGB2BGR)
                    result_bgr = cv2.resize(gen_bgr, (w_i, h_i))
                    current_app.logger.info(f'[ar-snapshot] Replicate ✓ "{style_name}"')
            except Exception as rep_err:
                current_app.logger.warning(f'[ar-snapshot] Replicate failed: {rep_err}')
                gen_pil = None

            # ── 2. OpenCV fallback ────────────────────────────────────────────
            if result_bgr is None:
                current_app.logger.info(f'[ar-snapshot] OpenCV fallback "{style_name}"')
                result_bgr = _opencv_render(img_bgr, lm, mask_fn, cfg, is_beard, 0)

            result_bgr = _apply_cinematic_yellow_tint(result_bgr)

            # ── Encode → base64 JPEG ──────────────────────────────────────────
            _, buf = cv2.imencode('.jpg', result_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
            result_b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode()

            return jsonify({
                'image':  result_b64,
                'source': 'replicate' if gen_pil is not None else 'opencv',
            })

        except Exception as e:
            current_app.logger.error(f'[ar-snapshot] {e}')
            return jsonify({'error': str(e)}), 500

        finally:
            for p in (tmp_path, mask_path):
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

    return analysis_bp

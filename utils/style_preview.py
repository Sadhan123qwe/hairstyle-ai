"""
Style Preview Generator
- Primary:  Replicate API (stable-diffusion-inpainting + SDXL)
- Fallback: Photorealistic 3D OpenCV renderer with multi-layer depth simulation
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)  # silence protobuf deprecation

import cv2, numpy as np, os, io, base64, time, requests, concurrent.futures, re, uuid, random, urllib.parse
import threading
import logging
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from dotenv import load_dotenv

load_dotenv()

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("style_preview")

# ── API settings ───────────────────────────────────────────────────────────────
REPLICATE_ENABLED = True   # Primary AI: Replicate inpainting + SDXL
HORDE_ENABLED     = False  # Disabled
POLLINATIONS_ENABLED = False  # Disabled

def _apply_cinematic_yellow_tint(img_bgr):
    """Adds a warm, golden cinematic 'Yellow' tint as requested by the user."""
    # Convert to float for precision
    img_f = img_bgr.astype(np.float32)
    # Increase Red and Green channels slightly, decrease Blue
    img_f[:,:,2] *= 1.10  # Red
    img_f[:,:,1] *= 1.05  # Green
    img_f[:,:,0] *= 0.85  # Blue
    # Subtle brightness/contrast boost
    img_f = np.clip(img_f * 1.02 + 5, 0, 255).astype(np.uint8)
    return img_f


# ══════════════════════════════════════════════════════════════════════════════
#   MASK SHAPE RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def _m(d, pts, fill=220): d.polygon(pts, fill=fill)
def _me(d, box, fill=220): d.ellipse(box, fill=fill)

def _s_pompadour(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    hw=int((rc[0]-lc[0])*1.15); hh=int(fy*0.60); cx=fx; top=max(0,fy-hh)
    _m(d,[(cx-hw//2-12,fy+15),(cx-hw//2,fy-hh//2),(cx-hw//4,top+hh//6),(cx,top),(cx+hw//4,top+hh//6),(cx+hw//2,fy-hh//2),(cx+hw//2+12,fy+15)])

def _s_side_part(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    hw=int((rc[0]-lc[0])*1.2); hh=int(fy*0.5); cx=fx; top=max(0,fy-hh)
    _m(d,[(cx-hw//2,fy+8),(cx-hw//2,top+hh//3),(cx-12,top),(cx+hw//2,top+hh//5),(cx+hw//2+18,fy+8)])

def _s_buzz_cut(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    # Tighter skull-cap for buzz cut
    hw=int((rc[0]-lc[0])*1.02); hh=int(fy*0.25); cx=fx; top=max(0,fy-hh)
    _me(d,[cx-hw//2,top,cx+hw//2,fy+5])

def _s_quiff(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    hw=int((rc[0]-lc[0])*1.1); hh=int(fy*0.62); cx=fx; top=max(0,fy-hh)
    _m(d,[(cx-hw//2-6,fy+12),(cx-hw//2,top+hh//2),(cx-hw//5,top+hh//4),(cx,top),(cx+hw//5,top+hh//4),(cx+hw//2,top+hh//2),(cx+hw//2+6,fy+12)])

def _s_slick_back(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    hw=int((rc[0]-lc[0])*1.12); hh=int(fy*0.44); cx=fx; top=max(0,fy-hh)
    _m(d,[(cx-hw//2-6,fy+10),(cx-hw//2+5,top+hh//3),(cx,top),(cx+hw//2-5,top+hh//3),(cx+hw//2+6,fy+10)])

def _s_faux_hawk(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    hw=int((rc[0]-lc[0])*1.1); sw=hw//4; hh=int(fy*0.70); cx=fx; top=max(0,fy-hh); st=fy-hh//3
    _m(d,[(cx-hw//2-6,fy+10),(cx-hw//2,st),(cx-sw//2,st),(cx-sw//2,fy+10)],fill=175)
    _m(d,[(cx+sw//2,fy+10),(cx+sw//2,st),(cx+hw//2,st),(cx+hw//2+6,fy+10)],fill=175)
    _m(d,[(cx-sw//2,fy+10),(cx-sw//2,st),(cx,top),(cx+sw//2,st),(cx+sw//2,fy+10)],fill=230)

def _s_undercut(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    hw=int((rc[0]-lc[0])*0.86); hh=int(fy*0.52); cx=fx; top=max(0,fy-hh)
    _m(d,[(cx-hw//2,fy+6),(cx-hw//2,top+hh//4),(cx-hw//4,top),(cx+hw//4,top),(cx+hw//2,top+hh//4),(cx+hw//2,fy+6)])

def _s_long_waves(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']; chin=lm['chin']
    hw=int((rc[0]-lc[0])*1.32); ht=max(0,fy-int(fy*0.44)); hb=min(h,chin[1]+int((h-chin[1])*0.58)); cx=fx
    _m(d,[(cx-hw//2-30,hb),(cx-hw//2-20,(ht+hb)//2),(cx-hw//2-5,ht+22),(cx-hw//4,ht),(cx+hw//4,ht),(cx+hw//2+5,ht+22),(cx+hw//2+20,(ht+hb)//2),(cx+hw//2+30,hb)])

def _s_bob(d, lm, w, h):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']; chin=lm['chin']
    hw=int((rc[0]-lc[0])*1.28); ht=max(0,fy-int(fy*0.42)); hb=int(chin[1]*0.88); cx=fx
    _m(d,[(cx-hw//2-20,hb),(cx-hw//2-12,(ht+hb)//2),(cx-hw//2,ht+12),(cx-hw//4,ht),(cx+hw//4,ht),(cx+hw//2,ht+12),(cx+hw//2+12,(ht+hb)//2),(cx+hw//2+20,hb)])

def _s_hair_generic(d, lm, w, h, idx=0):
    fx,fy=lm['forehead']; lc,rc=lm['left_cheek'],lm['right_cheek']
    # Increase variety in generic styles
    var_h = (0.35 + (idx % 7) * 0.08)
    var_w = (1.05 + (idx % 4) * 0.05)
    hw=int((rc[0]-lc[0])*var_w); hh=int(fy*var_h); cx=fx; top=max(0,fy-hh)
    _m(d,[(cx-hw//2,fy+8),(cx-hw//2,top+hh//3),(cx-hw//4,top),(cx+hw//4,top),(cx+hw//2,top+hh//3),(cx+hw//2,fy+8)])

# Beard masks
def _s_beard_full(d, lm, w, h):
    lj,rj=lm['left_jaw'],lm['right_jaw']; chin=lm['chin']; lc,rc=lm['left_cheek'],lm['right_cheek']
    _m(d,[(lc[0]-10,lj[1]-20),(lj[0]-10,lj[1]+4),(chin[0]-30,chin[1]+22),(chin[0],chin[1]+35),(chin[0]+30,chin[1]+22),(rj[0]+10,rj[1]+4),(rc[0]+10,rj[1]-20),(rc[0]-5,rj[1]-35),(rj[0]-2,lj[1]-10),(chin[0]+20,chin[1]+14),(chin[0],chin[1]+22),(chin[0]-20,chin[1]+14),(lj[0]+2,lj[1]-10),(lc[0]+5,rj[1]-35)],fill=235)

def _s_beard_stubble(d, lm, w, h):
    lj,rj=lm['left_jaw'],lm['right_jaw']; chin=lm['chin']; lc,rc=lm['left_cheek'],lm['right_cheek']
    # Thinner, more minimal stubble mask to avoid "full beard" bleed
    _m(d,[(lc[0]+12,lj[1]-5),(lj[0],lj[1]+2),(chin[0]-18,chin[1]+8),(chin[0],chin[1]+15),(chin[0]+18,chin[1]+8),(rj[0],rj[1]+2),(rc[0]-12,rj[1]-5),(rc[0]-22,rj[1]-15),(rj[0]-5,lj[1]-5),(chin[0]+10,chin[1]+6),(chin[0],chin[1]+10),(chin[0]-10,chin[1]+6),(lj[0]+5,lj[1]-5),(lc[0]+22,rj[1]-15)],fill=120)

def _s_beard_goatee(d, lm, w, h):
    chin=lm['chin']; lj,rj=lm['left_jaw'],lm['right_jaw']
    gw=int((rj[0]-lj[0])*0.36); cx=chin[0]; my=(lj[1]+chin[1])//2
    _m(d,[(cx-gw,my),(cx-gw-6,chin[1]+6),(cx,chin[1]+24),(cx+gw+6,chin[1]+6),(cx+gw,my),(cx+gw-8,my+12),(cx,chin[1]+12),(cx-gw+8,my+12)],fill=225)

def _s_beard_circle(d, lm, w, h):
    chin=lm['chin']; lj,rj=lm['left_jaw'],lm['right_jaw']
    gw=int((rj[0]-lj[0])*0.32); cx=chin[0]; my=(lj[1]+chin[1])//2
    _me(d,[cx-gw,my-6,cx+gw,chin[1]+22],fill=228)
    _me(d,[cx-gw-12,my-28,cx+gw+12,my-8],fill=228)

def _s_beard_chinstrap(d, lm, w, h):
    lj,rj=lm['left_jaw'],lm['right_jaw']; chin=lm['chin']; lc,rc=lm['left_cheek'],lm['right_cheek']; sw=20
    _m(d,[(lc[0]+8,lj[1]-28),(lj[0]-6,lj[1]+6),(lj[0]+sw,lj[1]+6),(lc[0]+8+sw,lj[1]-28)],fill=220)
    _m(d,[(rc[0]-8-sw,rj[1]-28),(rj[0]-sw,rj[1]+6),(rj[0]+6,rj[1]+6),(rc[0]-8,rj[1]-28)],fill=220)
    _m(d,[(lj[0]+sw,lj[1]+6),(chin[0]-22,chin[1]+22),(chin[0],chin[1]+32),(chin[0]+22,chin[1]+22),(rj[0]-sw,rj[1]+6),(rj[0]-sw,rj[1]-10),(chin[0]+12,chin[1]+16),(chin[0]-12,chin[1]+16),(lj[0]+sw,lj[1]-10)],fill=220)

def _s_beard_anchor(d, lm, w, h):
    chin=lm['chin']; lj,rj=lm['left_jaw'],lm['right_jaw']; cx=chin[0]; my=(lj[1]+chin[1])//2
    _m(d,[(cx-32,my+6),(cx-16,chin[1]-4),(cx,chin[1]+28),(cx+16,chin[1]-4),(cx+32,my+6),(cx+24,my+6),(cx+12,chin[1]),(cx,chin[1]+18),(cx-12,chin[1]),(cx-24,my+6)],fill=225)
    _me(d,[cx-30,my-30,cx+30,my-10],fill=225)

def _s_beard_garibaldi(d, lm, w, h):
    lj,rj=lm['left_jaw'],lm['right_jaw']; chin=lm['chin']; lc,rc=lm['left_cheek'],lm['right_cheek']; ex=18
    _m(d,[(lc[0]-ex,lj[1]-18),(lj[0]-ex,lj[1]+6),(chin[0]-38,chin[1]+44),(chin[0],chin[1]+60),(chin[0]+38,chin[1]+44),(rj[0]+ex,rj[1]+6),(rc[0]+ex,rj[1]-18),(rc[0]-4,rj[1]-32),(chin[0]+28,chin[1]+34),(chin[0],chin[1]+48),(chin[0]-28,chin[1]+34),(lc[0]+4,rj[1]-32)],fill=232)

HAIR_MASKS = {
    'classic pompadour':_s_pompadour,'pompadour':_s_pompadour,
    'side part':_s_side_part,'side part long top':_s_side_part,'side part with volume':_s_side_part,'angular fringe':_s_side_part,
    'buzz cut':_s_buzz_cut,
    'textured quiff':_s_quiff,'quiff':_s_quiff,'french crop':_s_quiff,'fringed crop':_s_quiff,
    'slick back':_s_slick_back,'slick back with fade':_s_slick_back,
    'faux hawk':_s_faux_hawk,'mohawk':_s_faux_hawk,
    'undercut':_s_undercut,'classic undercut':_s_undercut,'ivy league':_s_undercut,
    'beach waves':_s_long_waves,'straight & long':_s_long_waves,'lob with waves':_s_long_waves,
    'long layers':_s_long_waves,'wavy medium length':_s_long_waves,'textured waves':_s_long_waves,
    'shoulder length with curls':_s_long_waves,
    'bob cut':_s_bob,'blunt bob':_s_bob,'chin-length bob':_s_bob,'deep side part bob':_s_bob,
}
BEARD_MASKS = {
    'full beard':_s_beard_full,'natural beard':_s_beard_full,'short full beard':_s_beard_full,'beardstache':_s_beard_full,
    'full beard (width focus)':_s_beard_garibaldi,'garibaldi beard':_s_beard_garibaldi,
    'short boxed beard':_s_beard_chinstrap,'boxed beard':_s_beard_chinstrap,
    'stubble':_s_beard_stubble,'long stubble':_s_beard_stubble,
    'goatee':_s_beard_goatee,'extended goatee':_s_beard_goatee,'van dyke':_s_beard_goatee,
    'balbo':_s_beard_anchor,'balbo beard':_s_beard_anchor,'anchor beard':_s_beard_anchor,
    'horseshoe mustache':_s_beard_anchor,'handlebar mustache':_s_beard_anchor,'mustache only':_s_beard_anchor,
    'circle beard':_s_beard_circle,
    'chinstrap':_s_beard_chinstrap,'mutton chops':_s_beard_chinstrap,'sideburns only':_s_beard_chinstrap,
}

# Hair / beard color and strength presets — STRONG colors for visible changes
HAIR_CFG = {
    # Colors in BGR. These are DARK BROWN / NEAR-BLACK tones for realistic dark hair.
    # Do NOT use light values — they render as gray/silver.
    'classic pompadour': {'color':(18,12,5),    'blend':0.96},
    'side part':         {'color':(22,15,7),    'blend':0.94},
    'buzz cut':          {'color':(28,20,10),   'blend':0.93},
    'textured quiff':    {'color':(16,11,4),    'blend':0.96},
    'slick back':        {'color':(10,6,2),     'blend':0.97},
    'faux hawk':         {'color':(15,10,4),    'blend':0.96},
    'undercut':          {'color':(24,17,8),    'blend':0.94},
    'beach waves':       {'color':(50,35,16),   'blend':0.93},
    'bob cut':           {'color':(38,26,11),   'blend':0.94},
    '_default':          {'color':(20,13,5),    'blend':0.95},
}
BEARD_CFG = {
    'full beard':        {'color':(8,5,2),     'blend':0.97,'stipple':True},
    'short boxed beard': {'color':(10,6,2),    'blend':0.96,'stipple':True},
    'beardstache':       {'color':(8,5,2),     'blend':0.97,'stipple':True},
    'garibaldi beard':   {'color':(12,8,3),    'blend':0.97,'stipple':True},
    'stubble':           {'color':(30,22,12),  'blend':0.90,'stipple':True},
    'long stubble':      {'color':(22,15,7),   'blend':0.92,'stipple':True},
    'goatee':            {'color':(9,6,2),     'blend':0.96,'stipple':True},
    'extended goatee':   {'color':(10,6,2),    'blend':0.95,'stipple':True},
    'van dyke':          {'color':(10,6,2),    'blend':0.95,'stipple':True},
    'circle beard':      {'color':(9,6,2),     'blend':0.96,'stipple':True},
    'balbo beard':       {'color':(10,6,2),    'blend':0.95,'stipple':True},
    'anchor beard':      {'color':(8,5,2),     'blend':0.97,'stipple':True},
    'chinstrap':         {'color':(12,8,3),    'blend':0.96,'stipple':True},
    'horseshoe mustache':{'color':(9,6,2),     'blend':0.97,'stipple':True},
    'handlebar mustache':{'color':(10,6,2),    'blend':0.96,'stipple':True},
    '_default':          {'color':(9,6,2),     'blend':0.95,'stipple':True},
}


# ══════════════════════════════════════════════════════════════════════════════
#   REPLICATE API GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def _build_replicate_prompt(style_name, style_type):
    """Build an optimized prompt per style type."""
    base = "photorealistic portrait, professional photography, sharp focus, natural lighting"
    k = style_name.lower()
    if style_type == "hair":
        return f"a man with {style_name} hairstyle, {base}"
    elif style_type == "beard":
        return f"a man with {style_name} beard style, well-groomed, {base}"
    else:
        return f"a man with {style_name}, {base}"


def _save_mask_image(mask_np, out_path):
    """Save a numpy float32 mask [0..1] as a PNG file."""
    mask_u8 = (np.clip(mask_np, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(mask_u8, mode="L").save(out_path)


# Thread-based rate limiter: max 2 concurrent Replicate calls
_replicate_semaphore = threading.Semaphore(2)


def _replicate_inpainting(image_path, mask_path, style_name, style_type):
    """
    Call Replicate stable-diffusion-inpainting.
    Returns a PIL Image or None.
    """
    if not os.path.exists(mask_path):
        log.warning("[Replicate] Mask file not found: %s", mask_path)
        return None
    try:
        import replicate as _rep

        REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
        if not REPLICATE_TOKEN:
            log.error("[Replicate] REPLICATE_API_TOKEN not set in .env")
            return None
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_TOKEN

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        with open(mask_path, "rb") as f:
            mask_b64 = base64.b64encode(f.read()).decode()

        prompt = _build_replicate_prompt(style_name, style_type)
        log.info("[Replicate] Inpainting '%s' ...", style_name)

        output = _rep.run(
            "stability-ai/stable-diffusion-inpainting",
            input={
                "image": f"data:image/jpeg;base64,{img_b64}",
                "mask": f"data:image/png;base64,{mask_b64}",
                "prompt": prompt,
                "negative_prompt": "cartoon, blur, distorted, deformed, ugly, watermark, text",
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
            },
        )
        if output:
            resp = requests.get(str(output[0]), timeout=30)
            log.info("[Replicate] ✓ Inpainting success for '%s'", style_name)
            return Image.open(io.BytesIO(resp.content)).convert("RGB")
        return None
    except Exception as e:
        log.warning("[Replicate] Inpainting failed for '%s': %s", style_name, str(e)[:150])
        return None


def _replicate_sdxl(image_path, style_name, style_type):
    """
    Call Replicate SDXL img2img as a secondary attempt.
    Returns a PIL Image or None.
    """
    try:
        import replicate as _rep

        REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
        if not REPLICATE_TOKEN:
            return None

        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        prompt = _build_replicate_prompt(style_name, style_type)
        log.info("[Replicate] SDXL img2img '%s' ...", style_name)

        output = _rep.run(
            "stability-ai/sdxl",
            input={
                "image": f"data:image/jpeg;base64,{img_b64}",
                "prompt": prompt,
                "negative_prompt": "cartoon, deformed, blurry, ugly",
                "strength": 0.6,
                "num_inference_steps": 30,
            },
        )
        if output:
            resp = requests.get(str(output[0]), timeout=30)
            log.info("[Replicate] ✓ SDXL success for '%s'", style_name)
            return Image.open(io.BytesIO(resp.content)).convert("RGB")
        return None
    except Exception as e:
        log.warning("[Replicate] SDXL failed for '%s': %s", style_name, str(e)[:150])
        return None


def _replicate_generate(image_path, mask_path, style_name, style_type):
    """
    Primary AI entry point.
    1. Try Replicate inpainting.
    2. Try Replicate SDXL img2img.
    3. Return None → caller uses OpenCV fallback.
    """
    if not REPLICATE_ENABLED:
        return None
    with _replicate_semaphore:
        # 1. Inpainting
        gen = _replicate_inpainting(image_path, mask_path, style_name, style_type)
        if gen is not None:
            return gen
        # 2. SDXL
        gen = _replicate_sdxl(image_path, style_name, style_type)
        if gen is not None:
            return gen
    return None


# ══════════════════════════════════════════════════════════════════════════════
#   ADVANCED OPENCV FALLBACK (natural hair color sampling + photorealistic blend)
# ══════════════════════════════════════════════════════════════════════════════

def _build_mask(mask_fn, lm, w, h, blur_r=10):
    mi = Image.new("L",(w,h),0)
    mask_fn(ImageDraw.Draw(mi), lm, w, h)
    mi = mi.filter(ImageFilter.GaussianBlur(radius=blur_r))
    return np.array(mi, dtype=np.float32)/255.0


def _subtract_face_oval(mask, lm, w, h):
    """
    Erode the hair mask over the face region so hair never covers the face.
    Computes a soft Gaussian-feathered ellipse from forehead/chin/cheek landmarks
    and subtracts it from the mask.
    """
    fx, fy  = lm.get('forehead', (w//2, int(h*0.15)))
    chin    = lm.get('chin',     (w//2, int(h*0.85)))
    lcheek  = lm.get('left_cheek',  (int(w*0.25), int(h*0.50)))
    rcheek  = lm.get('right_cheek', (int(w*0.75), int(h*0.50)))

    cx     = (fx + chin[0]) // 2
    cy     = (fy + chin[1]) // 2
    half_w = int(abs(rcheek[0] - lcheek[0]) * 0.68)
    half_h = int(abs(chin[1]  - fy)         * 0.62)

    face_mi = Image.new("L", (w, h), 0)
    ImageDraw.Draw(face_mi).ellipse(
        [cx - half_w, cy - half_h, cx + half_w, cy + half_h], fill=255
    )
    face_mi  = face_mi.filter(ImageFilter.GaussianBlur(radius=max(12, half_w // 5)))
    face_np  = np.array(face_mi, dtype=np.float32) / 255.0
    return np.clip(mask - face_np, 0.0, 1.0)


def _sample_hair_color(img_bgr, lm, is_beard):
    """
    Sample the real hair/beard color from the photo.
    Returns a BGR tuple.
    """
    H, W = img_bgr.shape[:2]
    fx, fy = lm.get('forehead', (W//2, H//6))
    chin = lm.get('chin', (W//2, int(H*0.85)))

    samples = []
    if not is_beard:
        top_y = max(0, fy - int(fy * 0.55))
        y1, y2 = max(0, top_y - 20), min(H, top_y + 20)
        x1, x2 = max(0, fx - 30), min(W, fx + 30)
        patch = img_bgr[y1:y2, x1:x2]
        if patch.size > 0:
            samples.append(patch.reshape(-1, 3))
    else:
        by = min(H-1, chin[1] + 10)
        y1, y2 = max(0, by - 12), min(H, by + 20)
        x1, x2 = max(0, chin[0] - 22), min(W, chin[0] + 22)
        patch = img_bgr[y1:y2, x1:x2]
        if patch.size > 0:
            samples.append(patch.reshape(-1, 3))

    if samples:
        all_px = np.concatenate(samples, axis=0).astype(np.float32)
        dark_idx = np.argsort(all_px.mean(axis=1))
        pick = all_px[dark_idx[:max(1, len(dark_idx)//3)]].mean(axis=0)
        return tuple(int(v) for v in pick)
    return (20, 14, 7)


def _add_3d_hair_strands(img, mask_np, color_bgr, rng, is_beard):
    """
    Draw photorealistic 3D hair/beard strands with multiple layers:
    - Shadow underlayer for depth
    - Main color strands with flow direction
    - Highlight specular strands for shine
    """
    H, W = img.shape[:2]
    result = img.copy().astype(np.float32)
    m3 = mask_np[:, :, np.newaxis]

    # ── 1. Deep shadow underlayer ────────────────────────────────────────────
    shadow_mask = cv2.GaussianBlur(mask_np, (41, 41), 0)
    # For beards: only light shadow (0.15) so we don't turn the underlying skin gray.
    # For hair:   deeper shadow (0.45) to create volume/depth at the scalp.
    shadow_depth = 0.15 if is_beard else 0.45
    darken_factor = shadow_depth + (1.0 - shadow_depth) * (1.0 - shadow_mask)
    result *= darken_factor[:, :, np.newaxis]
    result = np.clip(result, 0, 255)

    # ── 2. Build coordinate arrays ───────────────────────────────────────────
    ys, xs = np.where(mask_np > 0.08)
    if len(xs) == 0:
        return np.clip(result, 0, 255).astype(np.uint8)

    b, g, r = color_bgr
    # Rich color variants — use PROPORTIONAL brightening (not flat +100)
    # Flat +100 on dark colors like (22,16,8) → (122,106,88) = GRAY!
    # Proportional: multiply by 1.4 so dark stays dark-ish, not silver.
    hi_b = min(255, int(b * 1.4 + 18))
    hi_g = min(255, int(g * 1.4 + 15))
    hi_r = min(255, int(r * 1.4 + 12))
    sh_b, sh_g, sh_r = max(0, b - 8), max(0, g - 7), max(0, r - 5)

    strand_canvas = np.clip(result, 0, 255).astype(np.uint8)

    # ── 3. Shadow strands (thick, dark, underlayer) ──────────────────────────
    n_shadow = 3000 if not is_beard else 3500
    chosen = rng.choice(len(xs), size=min(n_shadow, len(xs)), replace=False)
    for i in chosen:
        x0, y0 = int(xs[i]), int(ys[i])
        lmv = float(mask_np[y0, x0])
        if lmv < 0.15:
            continue
        sc = (max(0,b-30), max(0,g-28), max(0,r-25))
        if is_beard:
            dx, dy = int(rng.integers(-4, 5)), int(rng.integers(4, 14))
        else:
            cx = W // 2
            flow = (x0 - cx) // 8
            dx = flow + int(rng.integers(-5, 6))
            dy = int(rng.integers(10, 28))
        x1 = min(W-1, max(0, x0+dx))
        y1 = min(H-1, max(0, y0+dy))
        cv2.line(strand_canvas, (x0, y0), (x1, y1), sc, 2, cv2.LINE_AA)

    # ── 4. Main color strands (medium, varied) ───────────────────────────────
    n_main = 4000 if not is_beard else 4500
    chosen = rng.choice(len(xs), size=min(n_main, len(xs)), replace=False)
    for i in chosen:
        x0, y0 = int(xs[i]), int(ys[i])
        lmv = float(mask_np[y0, x0])
        if lmv < 0.1:
            continue
        jit = rng.integers(-15, 16, size=3)
        sc = (
            int(np.clip(b + jit[0], 0, 255)),
            int(np.clip(g + jit[1], 0, 255)),
            int(np.clip(r + jit[2], 0, 255)),
        )
        if is_beard:
            dx = int(rng.integers(-3, 4))
            dy = int(rng.integers(3, 12))
        else:
            cx = W // 2
            flow = (x0 - cx) // 10
            dx = flow + int(rng.integers(-4, 5))
            dy = int(rng.integers(8, 24))
        x1 = min(W-1, max(0, x0+dx))
        y1 = min(H-1, max(0, y0+dy))
        thick = 1 if rng.random() > 0.15 else 2
        cv2.line(strand_canvas, (x0, y0), (x1, y1), sc, thick, cv2.LINE_AA)

    # ── 5. Highlight/specular strands (thin, bright, top layer) ──────────────
    # Keep highlight count LOW for hair — too many = gray/silver wash
    n_hi = 400 if not is_beard else 600
    chosen = rng.choice(len(xs), size=min(n_hi, len(xs)), replace=False)
    for i in chosen:
        x0, y0 = int(xs[i]), int(ys[i])
        lmv = float(mask_np[y0, x0])
        if lmv < 0.3:
            continue
        sc = (hi_b + int(rng.integers(-10, 11)),
              hi_g + int(rng.integers(-10, 11)),
              hi_r + int(rng.integers(-10, 11)))
        sc = tuple(int(np.clip(v, 0, 255)) for v in sc)
        if is_beard:
            dx, dy = int(rng.integers(-2, 3)), int(rng.integers(2, 8))
        else:
            cx = W // 2
            dx = (x0 - cx) // 12 + int(rng.integers(-3, 4))
            dy = int(rng.integers(6, 18))
        x1 = min(W-1, max(0, x0+dx))
        y1 = min(H-1, max(0, y0+dy))
        cv2.line(strand_canvas, (x0, y0), (x1, y1), sc, 1, cv2.LINE_AA)

    # ── 6. Blend strands onto base with strong mask ──────────────────────────
    # For beards: use a very high blend factor so the dark strand color shows clearly.
    # For hair:   slightly lower since we want more natural integration.
    factor = 0.94 if not is_beard else 0.97
    blended = (
        img.astype(np.float32) * (1.0 - m3 * factor)
        + strand_canvas.astype(np.float32) * (m3 * factor)
    )
    return np.clip(blended, 0, 255).astype(np.uint8)


def _add_3d_lighting(img, mask_np, is_beard):
    """
    Add 3D directional lighting to simulate studio lighting on hair/beard.
    Light comes from top-left, creating natural depth and volume.
    """
    H, W = img.shape[:2]
    result = img.astype(np.float32)
    m3 = mask_np[:, :, np.newaxis]

    # Create directional gradient (light from top-left)
    y_grad = np.linspace(1.0, 0.0, H).reshape(-1, 1)  # top=bright, bottom=dark
    x_grad = np.linspace(0.8, 0.3, W).reshape(1, -1)   # left=bright, right=darker
    light_map = (y_grad * 0.6 + x_grad * 0.4)
    light_map = cv2.GaussianBlur(light_map.astype(np.float32), (51, 51), 0)

    # Apply lighting: brighten highlights, deepen shadows
    # Keep the highlight intensity LOW for hair — strong highlight = gray-silver look
    highlight = light_map * 18   # was 45, reduced to avoid silver washing
    shadow = (1.0 - light_map) * -20  # subtle shadow
    lighting = (highlight + shadow)[:, :, np.newaxis]

    result += lighting * m3

    # Add subtle specular gloss band across the top of the hair
    if not is_beard:
        gloss_y = int(H * 0.15)
        gloss_band = np.zeros((H, W), dtype=np.float32)
        gloss_h = max(1, int(H * 0.08))
        gy1, gy2 = max(0, gloss_y - gloss_h), min(H, gloss_y + gloss_h)
        gloss_band[gy1:gy2, :] = 1.0
        gloss_band = cv2.GaussianBlur(gloss_band, (31, 31), 0)
        gloss_band *= mask_np  # only within mask
        result += gloss_band[:, :, np.newaxis] * 35

    return np.clip(result, 0, 255).astype(np.uint8)


def _opencv_render(img_bgr, lm, mask_fn, cfg, is_beard, idx):
    """Photorealistic 3D renderer with multi-layer depth simulation."""
    h, w = img_bgr.shape[:2]
    mask = _build_mask(mask_fn, lm, w, h, blur_r=18)

    # For hair (not beard): remove the face oval so hair doesn't paint over the face
    if not is_beard:
        mask = _subtract_face_oval(mask, lm, w, h)

    # ── Sample real hair color and blend with style color ────────────────────
    sampled_color = _sample_hair_color(img_bgr, lm, is_beard)
    cfg_color = cfg['color']
    # For beards: use mostly style color (10% sampled) so dark CFG colors dominate.
    # For hair:   use low sampled color (15%) — cfg colors are already well-calibrated dark tones.
    #             Using 35% sampled was picking up gray scalp/skin, causing silver appearance.
    blend_ratio = 0.10 if is_beard else 0.15
    color = tuple(
        int(sampled_color[i] * blend_ratio + cfg_color[i] * (1 - blend_ratio))
        for i in range(3)
    )
    blend = cfg['blend']

    rng = np.random.default_rng(idx * 7 + 13)

    # ── 1. Strong base color fill layer ──────────────────────────────────────
    layer = np.full((h, w, 3), color, dtype=np.float32)
    # Add directional noise for texture
    noise = rng.integers(-22, 22, (h, w), dtype=np.int16).astype(np.float32)
    blur_k = (1, 15) if not is_beard else (3, 9)
    noise = cv2.GaussianBlur(noise, blur_k, 0)
    for c in range(3):
        layer[:, :, c] = np.clip(layer[:, :, c] + noise, 0, 255)

    # ── 2. Blend base layer STRONGLY onto image ──────────────────────────────
    m3 = mask[:, :, np.newaxis]
    blended = np.clip(
        img_bgr.astype(np.float32) * (1.0 - m3 * blend)
        + layer * (m3 * blend),
        0, 255
    ).astype(np.uint8)

    # ── 3. Add 3D photorealistic hair strands (3 layers) ────────────────────
    blended = _add_3d_hair_strands(blended, mask, color, rng, is_beard)

    # ── 4. Add 3D directional lighting ──────────────────────────────────────
    blended = _add_3d_lighting(blended, mask, is_beard)

    # ── 5. Edge depth / ambient occlusion at hair boundary ──────────────────
    edge = np.abs(cv2.Laplacian(mask, cv2.CV_32F))
    edge = cv2.GaussianBlur(edge, (7, 7), 0)
    edge = np.clip(edge * 5.0, 0, 0.5)[:, :, np.newaxis]
    blended = np.clip(blended.astype(np.float32) - edge * 40, 0, 255).astype(np.uint8)

    # ── 6. Sharpening for crispness ─────────────────────────────────────────
    kernel = np.array([[0,-0.4,0],[-0.4,2.6,-0.4],[0,-0.4,0]], dtype=np.float32)
    sharpened = cv2.filter2D(blended, -1, kernel)
    sharp_blend = np.clip(
        blended.astype(np.float32) * 0.45 + sharpened.astype(np.float32) * 0.55,
        0, 255
    ).astype(np.uint8)

    final = np.where(m3 > 0.1, sharp_blend, blended)
    return final.astype(np.uint8)


# ══════════════════════════════════════════════════════════════════════════════
#   MAIN RENDERER
# ══════════════════════════════════════════════════════════════════════════════

def _find(name, table):
    if not name: return None
    k = name.lower().strip()
    print(f"[Debug] Finding mask for: '{k}'")
    if k in table: 
        print(f"[Debug] Exact match found for: '{k}'")
        return table[k]
    # Use re to find word boundaries to avoid 'stubble' matching 'full beard' etc
    for key, val in table.items():
        if re.search(rf"\b{re.escape(key)}\b", k): 
            print(f"[Debug] Regex match found for: '{key}' in '{k}'")
            return val
    print(f"[Debug] No match found for: '{k}', using fallback.")
    return None

def _render_one(image_path, lm, style_name, mask_fn, cfg, is_beard, idx, prompt, denoise, out_path):
    try:
        orig_pil = Image.open(image_path).convert("RGB")
        w, h = orig_pil.size
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError("cv2 read failed")
        img_bgr = cv2.resize(img_bgr, (w, h))

        # Stagger: alternate slots get 1.5s delay to spread API calls
        stagger = max(0, (idx % 2) * 1.5)
        if stagger:
            time.sleep(stagger)

        result_bgr = None
        style_type  = "beard" if is_beard else "hair"

        # ── 1. Try Replicate (inpainting → SDXL) ──────────────────────────────
        if REPLICATE_ENABLED:
            log.info("[AI] Replicate for '%s' ...", style_name)
            # Save a temporary mask PNG for the inpainting call
            tmp_mask_path = out_path + "_mask.png"
            try:
                mask_np = _build_mask(mask_fn, lm, w, h, blur_r=18)
                _save_mask_image(mask_np, tmp_mask_path)
                gen = _replicate_generate(image_path, tmp_mask_path, style_name, style_type)
            except Exception as _re:
                log.error("[AI] Replicate exception for '%s': %s", style_name, _re)
                gen = None
            finally:
                if os.path.exists(tmp_mask_path):
                    os.remove(tmp_mask_path)

            if gen is not None:
                log.info("[AI] Replicate success for '%s'", style_name)
                gen_bgr = cv2.resize(cv2.cvtColor(np.array(gen), cv2.COLOR_RGB2BGR), (w, h))
                soft = _build_mask(mask_fn, lm, w, h, blur_r=20)
                m = soft[:, :, np.newaxis]

        # ── 2. OpenCV 3D fallback ────────────────────────────────────────────

        if result_bgr is None:
            log.info("[Fallback] OpenCV renderer for '%s'", style_name)
            lm_jitter = {k: (v[0]+random.randint(-8,8), v[1]+random.randint(-8,8)) for k,v in lm.items()}
            result_bgr = _opencv_render(img_bgr, lm_jitter, mask_fn, cfg, is_beard, idx)

        if result_bgr is not None:
            # Apply the "Wonderful" cinematic yellow grade
            result_bgr = _apply_cinematic_yellow_tint(result_bgr)

        cv2.imwrite(out_path, result_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return True
    except Exception as e:
        log.error("[render_one] '%s' failed: %s", style_name, e)
        # Never crash the pipeline — fall back gracefully
        try:
            img_bgr = cv2.imread(image_path)
            if img_bgr is not None:
                lm_jitter = {k: (v[0]+random.randint(-5,5), v[1]+random.randint(-5,5)) for k,v in lm.items()}
                result_bgr = _opencv_render(img_bgr, lm_jitter, mask_fn, cfg, is_beard, idx)
                cv2.imwrite(out_path, result_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
                return True
        except Exception:
            pass
        return False


def _hair_prompt(name, face_shape, gender, idx=0):
    adjectives = ["classic", "modern", "stylish", "bold", "clean", "trendy", "sophisticated"]
    adj = adjectives[idx % len(adjectives)]
    k = name.lower()
    # Powerful negative prompts to force accuracy
    neg = "### beard, mustache, facial hair, long hair" if ("buzz" in k or "short" in k) else "### messy hair, distorted face"
    
    return (f"Professional studio portrait of a person with a {adj} {name} hairstyle. "
            f"Style focus: {name}. Warm cinematic golden lighting, professional studio photography, 8k masterpiece. "
            f"The man has a {face_shape} face shape. "
            f"Ultra-detailed hair follicles, sharp focus. {neg}")

def _beard_prompt(name, face_shape, idx=0):
    # Differentiate stubble from thick beards
    k = name.lower()
    if "stubble" in k:
        look = "light, rugged, closely trimmed 3-day facial stubble shadow"
        neg = "### full beard, long hair, thick beard, goatee"
    elif "goatee" in k or "van dyke" in k:
        look = "precise, sharp, perfectly groomed goatee and mustache"
        neg = "### full beard, sideburns, thick beard, mutton chops"
    else:
        look = f"thick, dense, voluminous, well-defined {name} beard"
        neg = "### shaven face, hairless skin, smooth chin"
    
    adjectives = ["professional", "rugged", "dapper", "rugged", "refined", "masculine", "elegant"]
    adj = adjectives[idx % len(adjectives)]
    
    return (f"Close-up high-contrast studio portrait of a man with a {adj} {look}. "
            f"Style focus: {name}. High-end warm cinematic lighting, studio depth, 8k masterpiece. "
            f"The man has a {face_shape} face shape. "
            f"Extreme detail, sharp focus on hair follicles, photorealistic. {neg}")


def generate_previews(image_path, landmarks, hairstyles, beard_styles, upload_folder,
                      face_shape="oval", gender="male"):
    """
    Generate visual style preview images for each recommended style.
    - Max 5 hair + 5 beard styles.
    - Max 2 concurrent Gemini requests (via semaphore inside _gemini_generate).
    - Always returns 5+5 entries (None filename if generation failed).
    """
    prev_dir = os.path.join(upload_folder, 'previews')
    os.makedirs(prev_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(image_path))[0]

    # Guarantee exactly 5 styles each
    hairstyles   = list(hairstyles)[:5]
    beard_styles = list(beard_styles)[:5]

    tasks = []

    # Hair tasks
    for idx, style in enumerate(hairstyles):
        name   = style['name']
        mfn    = _find(name, HAIR_MASKS) or (lambda d, lm, w, h, i=idx: _s_hair_generic(d, lm, w, h, i))
        cfg    = _find(name, HAIR_CFG)   or HAIR_CFG['_default']
        prompt = _hair_prompt(name, face_shape, gender, idx)
        ts     = int(time.time() * 1000)
        out_r  = f"uploads/previews/{base}_hair_{idx}_{ts}.jpg"
        out_p  = os.path.join(prev_dir, f"{base}_hair_{idx}_{ts}.jpg")
        tasks.append({
            'type': 'hair', 'idx': idx,
            'image_path': image_path, 'landmarks': landmarks,
            'style_name': name, 'mask_fn': mfn, 'cfg': cfg, 'is_beard': False,
            'prompt': prompt, 'denoise': 0.85,
            'out_path': out_p, 'out_rel': out_r, 'style_dict': style,
        })

    # Beard tasks
    for idx, style in enumerate(beard_styles):
        name   = style['name']
        mfn    = _find(name, BEARD_MASKS) or (lambda d, lm, w, h, i=idx: _s_beard_garibaldi(d, lm, w, h) if i % 2 == 0 else _s_beard_full(d, lm, w, h))
        cfg    = _find(name, BEARD_CFG)   or BEARD_CFG['_default']
        prompt = _beard_prompt(name, face_shape, idx)
        ts     = int(time.time() * 1000)
        out_r  = f"uploads/previews/{base}_beard_{idx}_{ts}.jpg"
        out_p  = os.path.join(prev_dir, f"{base}_beard_{idx}_{ts}.jpg")
        tasks.append({
            'type': 'beard', 'idx': idx,
            'image_path': image_path, 'landmarks': landmarks,
            'style_name': name, 'mask_fn': mfn, 'cfg': cfg, 'is_beard': True,
            'prompt': prompt, 'denoise': 0.90,
            'out_path': out_p, 'out_rel': out_r, 'style_dict': style,
        })

    # Pre-fill with None so indices are always present
    hair_previews  = [None] * len(hairstyles)
    beard_previews = [None] * len(beard_styles)

    log.info("[Core] Starting generation for %d styles (max 2 concurrent Gemini calls)...", len(tasks))

    def do_task(t):
        try:
            ok = _render_one(
                t['image_path'], t['landmarks'], t['style_name'],
                t['mask_fn'], t['cfg'], t['is_beard'], t['idx'],
                t['prompt'], t['denoise'], t['out_path']
            )
            return t, ok
        except Exception as ex:
            log.error("[Core] do_task '%s' crashed: %s", t['style_name'], ex)
            return t, False

    # Limit thread workers to 5 — semaphore inside _gemini_generate caps Gemini to 2
    max_workers = min(len(tasks), 5)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(do_task, t): t for t in tasks}

        for future in concurrent.futures.as_completed(future_to_task):
            t  = future_to_task[future]
            try:
                t, ok = future.result(timeout=180)
            except Exception as ex:
                log.error("[Core] Future for '%s' errored: %s", t['style_name'], ex)
                ok = False

            result_dict = {
                'filename': t['out_rel'] if ok else None,
                'name': t['style_name'],
                'description': t['style_dict'].get('description', ''),
            }
            if t['type'] == 'hair':
                hair_previews[t['idx']] = result_dict
            else:
                beard_previews[t['idx']] = result_dict

    log.info("[Core] Generation complete: %d hair, %d beard previews.",
             sum(1 for p in hair_previews  if p and p.get('filename')),
             sum(1 for p in beard_previews if p and p.get('filename')))

    return {'hair_previews': hair_previews, 'beard_previews': beard_previews}

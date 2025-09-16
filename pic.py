# app_streamlit_puzzle.py

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import random
import io

# ---------- Placeholder Image ----------
def make_placeholder_image(prompt, size=(512, 512)):
    w, h = size
    img = Image.new("RGB", (w, h), (240, 245, 255))
    draw = ImageDraw.Draw(img)

    # decorative shapes
    for _ in range(12):
        x0, y0 = random.randint(0, w-100), random.randint(0, h-100)
        x1, y1 = x0 + random.randint(50, 200), y0 + random.randint(50, 200)
        color = (random.randint(100, 220), random.randint(100, 220), random.randint(100, 220))
        draw.ellipse([x0, y0, x1, y1], fill=color)

    # prompt text
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except:
        font = ImageFont.load_default()

    if hasattr(draw, "textbbox"):
        bbox = draw.textbbox((0, 0), prompt, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    else:
        tw, th = font.getsize(prompt)

    draw.text(((w-tw)//2, (h-th)//2), prompt, fill="black", font=font)
    return img

# ---------- Puzzle Logic ----------
def split_image_to_tiles(image, grid_size):
    w, h = image.size
    tile_w, tile_h = w//grid_size, h//grid_size
    tiles = []
    for r in range(grid_size):
        for c in range(grid_size):
            tile = image.crop((c*tile_w, r*tile_h, (c+1)*tile_w, (r+1)*tile_h))
            tiles.append(tile)
    blank = Image.new("RGB", (tile_w, tile_h), (200, 200, 200))
    tiles[-1] = blank
    return tiles

def shuffle_tiles(tiles):
    perm = list(range(len(tiles)))
    random.shuffle(perm)
    return [tiles[i] for i in perm], perm

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Concept → Puzzle", layout="wide")
st.title("🖼 Concept → Sliding Puzzle (Fast, Free)")

prompt = st.text_input("Enter a concept / prompt:", value="A sunny day at the beach")
grid_size = st.slider("Grid size:", min_value=2, max_value=6, value=3)

if st.button("Generate Image & Puzzle"):
    image = make_placeholder_image(prompt)
    img_resized = image.resize((grid_size*128, grid_size*128))
    st.session_state.tiles = split_image_to_tiles(img_resized, grid_size)
    st.session_state.shuffled_tiles, st.session_state.perm = shuffle_tiles(st.session_state.tiles)
    st.session_state.blank_idx = grid_size*grid_size - 1
    st.session_state.solved = False
    st.session_state.original_image = image

if "original_image" in st.session_state:
    st.image(st.session_state.original_image, caption="Placeholder Image", use_column_width=False)

# Puzzle Grid
if "shuffled_tiles" in st.session_state:
    n = grid_size
    for r in range(n):
        cols = st.columns(n)
        for c in range(n):
            idx = r*n + c
            tile_img = st.session_state.shuffled_tiles[idx]
            buf = io.BytesIO()
            tile_img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            if cols[c].button("", key=f"tile_{idx}"):
                br, bc = divmod(st.session_state.blank_idx, n)
                if (abs(r-br)==1 and c==bc) or (abs(c-bc)==1 and r==br):
                    st.session_state.shuffled_tiles[idx], st.session_state.shuffled_tiles[st.session_state.blank_idx] = \
                        st.session_state.shuffled_tiles[st.session_state.blank_idx], st.session_state.shuffled_tiles[idx]
                    st.session_state.perm[idx], st.session_state.perm[st.session_state.blank_idx] = \
                        st.session_state.perm[st.session_state.blank_idx], st.session_state.perm[idx]
                    st.session_state.blank_idx = idx
                    if st.session_state.perm == list(range(n*n)):
                        st.session_state.solved = True
            cols[c].image(img_bytes, use_column_width=True)

    if st.session_state.solved:
        st.success("🎉 Puzzle Solved!")
        

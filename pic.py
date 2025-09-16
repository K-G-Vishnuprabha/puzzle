# concept_puzzle_app_streamlit.py

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import random

# ---------- FAST PLACEHOLDER IMAGE ----------
def make_placeholder_image(prompt, size=(512, 512)):
    """Instant placeholder image with prompt text."""
    w, h = size
    img = Image.new("RGB", (w, h), (240, 245, 255))
    draw = ImageDraw.Draw(img)

    # decorative shapes
    for _ in range(12):
        x0, y0 = random.randint(0, w-100), random.randint(0, h-100)
        x1, y1 = x0 + random.randint(50, 200), y0 + random.randint(50, 200)
        color = (
            random.randint(100, 220),
            random.randint(100, 220),
            random.randint(100, 220)
        )
        draw.ellipse([x0, y0, x1, y1], fill=color)

    # prompt text
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except:
        font = ImageFont.load_default()
    tw, th = draw.textsize(prompt, font=font)
    draw.text(((w - tw)//2, (h - th)//2), prompt, fill="black", font=font)
    return img

# ---------- Puzzle logic ----------
def split_image_to_tiles(image, grid_size):
    w, h = image.size
    n = grid_size
    tile_w, tile_h = w // n, h // n
    tiles = []
    for row in range(n):
        for col in range(n):
            left, top = col * tile_w, row * tile_h
            right, bottom = left + tile_w, top + tile_h
            tile = image.crop((left, top, right, bottom))
            tiles.append(tile)
    blank = Image.new("RGB", (tile_w, tile_h), (200, 200, 200))
    tiles[-1] = blank
    return tiles

def shuffle_tiles(tiles):
    perm = list(range(len(tiles)))
    random.shuffle(perm)
    return [tiles[i] for i in perm], perm

# ---------- Streamlit App ----------
st.set_page_config(page_title="Concept → Puzzle", layout="wide")

st.title("🖼 Concept → Sliding Puzzle (Fast, Offline)")

prompt = st.text_input("Enter a concept / prompt:", value="A sunny day at the beach")
grid_size = st.slider("Grid size:", min_value=2, max_value=6, value=3)

if st.button("Generate Image"):
    st.session_state.image = make_placeholder_image(prompt)
    st.session_state.tiles = split_image_to_tiles(st.session_state.image.resize((grid_size*128, grid_size*128)), grid_size)
    st.session_state.shuffled_tiles, st.session_state.perm = shuffle_tiles(st.session_state.tiles)
    st.session_state.blank_idx = grid_size*grid_size - 1
    st.session_state.solved = False

if "image" in st.session_state:
    st.image(st.session_state.image, caption="Placeholder Image", use_column_width=False)

if "shuffled_tiles" in st.session_state:
    st.subheader("🧩 Puzzle")
    cols = st.columns(grid_size)
    for i, col in enumerate(cols):
        for j in range(grid_size):
            idx = i*grid_size + j
            tile_img = st.session_state.shuffled_tiles[idx]
            if st.button("", key=f"tile_{idx}", help="Click to move"):
                # Move tile if adjacent to blank
                n = grid_size
                r, c = divmod(idx, n)
                br, bc = divmod(st.session_state.blank_idx, n)
                if (abs(r-br) == 1 and c==bc) or (abs(c-bc)==1 and r==br):
                    st.session_state.shuffled_tiles[idx], st.session_state.shuffled_tiles[st.session_state.blank_idx] = \
                        st.session_state.shuffled_tiles[st.session_state.blank_idx], st.session_state.shuffled_tiles[idx]
                    st.session_state.perm[idx], st.session_state.perm[st.session_state.blank_idx] = \
                        st.session_state.perm[st.session_state.blank_idx], st.session_state.perm[idx]
                    st.session_state.blank_idx = idx
                    # Check solved
                    if st.session_state.perm == list(range(grid_size*grid_size)):
                        st.session_state.solved = True
    if st.session_state.solved:
        st.success("🎉 Puzzle Solved!")
        
        

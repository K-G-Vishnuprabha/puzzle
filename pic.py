# app_sd_puzzle.py

import streamlit as st
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline
import random
import io

# ---------- Initialize Stable Diffusion ----------
@st.cache_resource
def load_model():
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16
    )
    pipe = pipe.to("cuda" if torch.cuda.is_available() else "cpu")
    return pipe

pipe = load_model()

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

# ---------- Streamlit UI ----------
st.set_page_config(page_title="AI Concept Puzzle", layout="wide")
st.title("🖼 AI Concept → Sliding Puzzle (Offline, Free)")

prompt = st.text_input("Enter a concept / prompt:", value="A sunny day at the beach")
grid_size = st.slider("Grid size:", min_value=2, max_value=6, value=3)

# Generate AI image
if st.button("Generate AI Image"):
    with st.spinner("Generating AI image... This may take a few seconds."):
        image = pipe(prompt).images[0]
        # Resize to square
        side = min(image.size)
        img_cropped = image.crop((
            (image.size[0]-side)//2,
            (image.size[1]-side)//2,
            (image.size[0]+side)//2,
            (image.size[1]+side)//2
        ))
        img_resized = img_cropped.resize((grid_size*128, grid_size*128))
        st.session_state.tiles = split_image_to_tiles(img_resized, grid_size)
        st.session_state.shuffled_tiles, st.session_state.perm = shuffle_tiles(st.session_state.tiles)
        st.session_state.blank_idx = grid_size*grid_size - 1
        st.session_state.solved = False
        st.session_state.original_image = image

# Show AI-generated image
if "original_image" in st.session_state:
    st.image(st.session_state.original_image, caption="AI Generated Image", use_column_width=False)

# Puzzle
if "shuffled_tiles" in st.session_state:
    st.subheader("🧩 Puzzle")
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
                if (abs(r-br) == 1 and c==bc) or (abs(c-bc) == 1 and r==br):
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
        

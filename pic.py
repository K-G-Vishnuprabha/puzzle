concept_puzzle_app.py
"""
Standalone Python Tkinter app:
- Generate an image from a text concept (uses OpenAI Images API if OPENAI_API_KEY is set).
- Fallback to a generated placeholder image (PIL) if no API key or API call fails.
- Convert image into sliding puzzle (NxN), shuffle to a solvable state, and allow play.
"""

import os
import io
import math
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont

# Optional: openai image generation (only used if API key provided)
try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# ---------- Helpers for image generation ----------

def try_generate_image_with_openai(prompt, size=(512, 512), api_key=None):
    """
    Try to generate an image with OpenAI Image API (DALL·E style).
    Returns a PIL.Image on success, raises Exception on failure.
    NOTE: This function is best-effort and may fail if openai library or API differs.
    """
    if not OPENAI_AVAILABLE:
        raise RuntimeError("openai package not installed.")
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("No OpenAI API key provided.")
    openai.api_key = api_key

    # Use the older openai.Image.create pattern (works for many setups).
    # If the user has a different OpenAI client, this may need update.
    resp = openai.Image.create(prompt=prompt, n=1, size=f"{size[0]}x{size[1]}")
    b64 = resp['data'][0]['b64_json']
    import base64
    img_data = base64.b64decode(b64)
    return Image.open(io.BytesIO(img_data)).convert("RGBA")


def make_placeholder_image(prompt, size=(512, 512)):
    """
    Create a visually pleasing placeholder image using PIL based on the prompt text.
    """
    w, h = size
    img = Image.new("RGB", (w, h), (240, 245, 255))
    draw = ImageDraw.Draw(img)

    # draw some decorative shapes
    for i in range(12):
        # random translucent ellipses
        bbox = [
            random.randint(-w//2, w),
            random.randint(-h//2, h),
            random.randint(w//4, w + w//2),
            random.randint(h//4, h + h//2),
        ]
        color = (
            random.randint(120, 220),
            random.randint(110, 200),
            random.randint(120, 220),
            50
        )
        try:
            draw.ellipse(bbox, fill=color)
        except Exception:
            pass

    # write the prompt text centered
    try:
        # try to load a common font; fallback to default
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    lines = []
    words = prompt.strip().split()
    # wrap words to reasonable line width
    max_chars = 24
    line = ""
    for w0 in words:
        if len(line) + len(w0) + 1 <= max_chars:
            line = (line + " " + w0).strip()
        else:
            lines.append(line)
            line = w0
    if line:
        lines.append(line)

    y = h//2 - (len(lines) * 18)
    for i, ln in enumerate(lines):
        tw, th = draw.textsize(ln, font=font)
        draw.text(((w - tw)//2, y + i*36), ln, fill=(20, 30, 60), font=font)

    # small caption
    caption = "Placeholder image (no API key)"
    tw, th = draw.textsize(caption, font=font)
    draw.text(((w - tw)//2, h - 40), caption, fill=(70, 80, 110), font=font)

    return img


# ---------- Puzzle logic ----------

def split_image_to_tiles(image, grid_size):
    """Return list of tiles (PIL Images) in row-major order. Last tile is the 'blank' tile."""
    w, h = image.size
    n = grid_size
    tile_w = w // n
    tile_h = h // n
    tiles = []
    for row in range(n):
        for col in range(n):
            left = col * tile_w
            top = row * tile_h
            right = left + tile_w
            bottom = top + tile_h
            tile = image.crop((left, top, right, bottom))
            tiles.append(tile)
    # The puzzle uses the last tile as blank: make it solid color
    blank = Image.new("RGBA", (tile_w, tile_h), (240,240,240,255))
    tiles[-1] = blank
    return tiles

def tiles_to_image(tiles, grid_size):
    """Reconstruct full image from tiles (useful for checking solution)."""
    n = grid_size
    tile_w, tile_h = tiles[0].size
    img = Image.new("RGBA", (tile_w * n, tile_h * n))
    idx = 0
    for r in range(n):
        for c in range(n):
            img.paste(tiles[idx], (c*tile_w, r*tile_h))
            idx += 1
    return img

def is_solvable(permutation, grid_size):
    """
    Check solvability for an sliding puzzle given the permutation list of tile indices (0..N-1),
    where the blank tile index is N-1 (last).
    permutation is a list giving which original tile is placed at each position (row-major).
    """
    N = len(permutation)
    # Flatten excluding the blank (value N-1)
    arr = [p for p in permutation if p != N-1]
    inv_count = 0
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] > arr[j]:
                inv_count += 1
    if grid_size % 2 == 1:
        # odd grid: solvable if inversions even
        return (inv_count % 2) == 0
    else:
        # even grid: puzzle is solvable if:
        # blank row counting from bottom (1-based) + inversions is even
        blank_index = permutation.index(N-1)
        row_from_top = blank_index // grid_size
        row_from_bottom = grid_size - row_from_top
        return ((inv_count + row_from_bottom) % 2) == 0

def make_solvable_permutation(n_tiles, grid_size):
    """Return a random permutation of 0..n_tiles-1 that is solvable."""
    perm = list(range(n_tiles))
    while True:
        random.shuffle(perm)
        if is_solvable(perm, grid_size) and perm != list(range(n_tiles)):
            return perm

# ---------- Tkinter UI & Game ----------

class PuzzleApp:
    def _init_(self, root):
        self.root = root
        root.title("Concept → Image → Sliding Puzzle")
        self.image = None      # PIL image (original generated)
        self.tiles = None      # list of PIL tiles (ordered by original index)
        self.grid_size = 3
        self.tile_imgs_tk = [] # PhotoImage objects for tkinter
        self.current_perm = None
        self.tile_buttons = []
        self.blank_pos = None

        self.setup_ui()

    def setup_ui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # top controls
        top = ttk.Frame(frm)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Concept / Prompt:").grid(row=0, column=0, sticky="w")
        self.prompt_var = tk.StringVar(value="A cozy cottage by the sea, watercolor")
        self.prompt_entry = ttk.Entry(top, textvariable=self.prompt_var, width=60)
        self.prompt_entry.grid(row=0, column=1, padx=6, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Button(top, text="Generate Image", command=self.on_generate).grid(row=0, column=2, padx=6)
        ttk.Button(top, text="Load Image...", command=self.on_load_image).grid(row=0, column=3, padx=6)
        ttk.Button(top, text="Save Image...", command=self.on_save_image).grid(row=0, column=4, padx=6)

        # API key
        keyrow = ttk.Frame(frm)
        keyrow.grid(row=1, column=0, sticky="ew", pady=(6,0))
        ttk.Label(keyrow, text="OpenAI API Key (optional):").grid(row=0, column=0, sticky="w")
        self.api_var = tk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
        self.api_entry = ttk.Entry(keyrow, textvariable=self.api_var, width=60, show="*" )
        self.api_entry.grid(row=0, column=1, sticky="ew", padx=6)
        keyrow.columnconfigure(1, weight=1)
        ttk.Label(keyrow, text="(Leave empty to use offline placeholder)").grid(row=0, column=2, sticky="w")

        # puzzle controls
        pctrl = ttk.Frame(frm)
        pctrl.grid(row=2, column=0, sticky="ew", pady=(8,6))
        ttk.Label(pctrl, text="Grid size:").grid(row=0, column=0, sticky="w")
        self.grid_var = tk.IntVar(value=3)
        grid_spin = ttk.Spinbox(pctrl, from_=2, to=6, textvariable=self.grid_var, width=4)
        grid_spin.grid(row=0, column=1, padx=6, sticky="w")

        ttk.Button(pctrl, text="Create Puzzle", command=self.on_create_puzzle).grid(row=0, column=2, padx=8)
        ttk.Button(pctrl, text="Shuffle (new)", command=self.on_shuffle).grid(row=0, column=3, padx=4)
        ttk.Button(pctrl, text="Reset (solve)", command=self.on_reset).grid(row=0, column=4, padx=4)

        # canvas/frame for puzzle
        board_frame = ttk.Frame(frm, borderwidth=2, relief="sunken")
        board_frame.grid(row=3, column=0, sticky="nsew")
        frm.rowconfigure(3, weight=1)
        self.board_frame = board_frame
        self.board_canvas = ttk.Frame(board_frame)
        self.board_canvas.pack(expand=True, fill="both", padx=4, pady=4)

        # status
        self.status_var = tk.StringVar(value="No image yet.")
        status = ttk.Label(frm, textvariable=self.status_var)
        status.grid(row=4, column=0, sticky="we", pady=(6,0))

    def set_status(self, txt):
        self.status_var.set(txt)

    def on_generate(self):
        prompt = self.prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning("Empty prompt", "Please type a concept/prompt first.")
            return
        self.set_status("Generating image...")
        self.root.update_idletasks()
        # Try OpenAI if key set
        api_key = self.api_var.get().strip() or os.getenv("OPENAI_API_KEY")
        generated = None
        if api_key and OPENAI_AVAILABLE:
            try:
                img = try_generate_image_with_openai(prompt, size=(512,512), api_key=api_key)
                generated = img.convert("RGBA")
                self.set_status("Image generated via OpenAI.")
            except Exception as e:
                # fail gracefully to placeholder
                self.set_status(f"OpenAI generation failed, using placeholder. ({e})")
                try:
                    generated = make_placeholder_image(prompt, size=(512,512)).convert("RGBA")
                except Exception as e2:
                    messagebox.showerror("Image generation error", f"Both OpenAI and placeholder failed: {e2}")
                    return
        else:
            # offline placeholder
            try:
                generated = make_placeholder_image(prompt, size=(512,512)).convert("RGBA")
                self.set_status("Placeholder image created (no API key).")
            except Exception as e:
                messagebox.showerror("Generation error", f"Could not create placeholder image: {e}")
                return

        self.image = generated
        self.show_image_preview()
        # auto-create puzzle with current grid size
        self.on_create_puzzle()

    def on_load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", ".png;.jpg;.jpeg;.bmp;.gif"),("All files",".*")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Open error", f"Could not open image: {e}")
            return
        # resize to reasonable square-ish for puzzle
        max_dim = 600
        w,h = img.size
        scale = min(max_dim/w, max_dim/h, 1.0)
        if scale < 1.0:
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        self.image = img
        self.set_status(f"Loaded image '{os.path.basename(path)}'.")
        self.show_image_preview()
        self.on_create_puzzle()

    def on_save_image(self):
        if not self.image:
            messagebox.showinfo("No image", "No image to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG image","*.png")])
        if not path:
            return
        try:
            self.image.save(path)
            self.set_status(f"Saved image to {path}")
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save: {e}")

    def show_image_preview(self):
        # show a thumbnail above the board (replace board with a label when no puzzle)
        for child in self.board_canvas.winfo_children():
            child.destroy()
        if not self.image:
            return
        # make a PhotoImage for display
        preview = self.image.copy()
        preview.thumbnail((240,240), Image.LANCZOS)
        self.preview_tk = ImageTk.PhotoImage(preview)
        lbl = ttk.Label(self.board_canvas, image=self.preview_tk)
        lbl.pack(padx=8, pady=8)
        self.board_canvas.update()

    def on_create_puzzle(self):
        if not self.image:
            messagebox.showinfo("No image", "Please generate or load an image first.")
            return
        n = int(self.grid_var.get())
        if n < 2 or n > 6:
            messagebox.showwarning("Grid size", "Grid size must be between 2 and 6.")
            return
        self.grid_size = n
        # ensure image is square by cropping or padding
        w,h = self.image.size
        side = min(w,h)
        img_cropped = self.image.crop(((w-side)//2, (h-side)//2, (w+side)//2, (h+side)//2))
        # resize to n * tile_size with tile_size = 128 (or adaptively)
        tile_size = max(64, min(160, 512 // n))
        full_size = tile_size * n
        img_for_tiles = img_cropped.resize((full_size, full_size), Image.LANCZOS)
        self.tiles = split_image_to_tiles(img_for_tiles, n)
        # Keep original tile order as 'solved' reference
        self.n_tiles = len(self.tiles)
        # create a solvable permutation and apply it
        self.current_perm = make_solvable_permutation(self.n_tiles, n)
        self.blank_pos = self.current_perm.index(self.n_tiles - 1)
        self.render_tiles()
        self.set_status(f"Puzzle created: {n}x{n}. Click tiles to slide.")

    def on_shuffle(self):
        if not self.tiles:
            messagebox.showinfo("No puzzle", "Create a puzzle first.")
            return
        self.current_perm = make_solvable_permutation(self.n_tiles, self.grid_size)
        self.blank_pos = self.current_perm.index(self.n_tiles - 1)
        self.render_tiles()
        self.set_status("Shuffled puzzle.")

    def on_reset(self):
        if not self.tiles:
            return
        self.current_perm = list(range(self.n_tiles))
        self.blank_pos = self.n_tiles - 1
        self.render_tiles()
        self.set_status("Reset: solved state.")

    def render_tiles(self):
        # clear board
        for child in self.board_canvas.winfo_children():
            child.destroy()
        n = self.grid_size
        tile_w, tile_h = self.tiles[0].size
        # create PhotoImage objects in order of current_perm for tkinter
        self.tile_imgs_tk = []
        for idx_in_board in range(self.n_tiles):
            orig_tile_idx = self.current_perm[idx_in_board]
            pil_tile = self.tiles[orig_tile_idx]
            # add a border to each tile for clarity
            display_tile = pil_tile.copy()
            draw = ImageDraw.Draw(display_tile)
            draw.rectangle([0,0,display_tile.size[0]-1, display_tile.size[1]-1], outline=(160,160,160,255))
            tkimg = ImageTk.PhotoImage(display_tile)
            self.tile_imgs_tk.append(tkimg)

        # grid of buttons
        self.tile_buttons = []
        for pos in range(self.n_tiles):
            r = pos // n
            c = pos % n
            btn = ttk.Button(self.board_canvas, image=self.tile_imgs_tk[pos], command=lambda p=pos: self.on_tile_click(p))
            btn.grid(row=r, column=c, padx=0, pady=0)
            self.tile_buttons.append(btn)
        self.board_canvas.update()

    def on_tile_click(self, pos):
        if not self.tiles:
            return
        n = self.grid_size
        r = pos // n
        c = pos % n
        br = self.blank_pos // n
        bc = self.blank_pos % n
        # if clicked tile is adjacent to blank, swap
        if (abs(r - br) == 1 and c == bc) or (abs(c - bc) == 1 and r == br):
            # swap positions in current_perm
            self.current_perm[self.blank_pos], self.current_perm[pos] = self.current_perm[pos], self.current_perm[self.blank_pos]
            self.blank_pos = pos
            self.render_tiles()
            if self.current_perm == list(range(self.n_tiles)):
                self.set_status("Solved! 🎉")
                messagebox.showinfo("Congratulations", "You solved the puzzle!")
            else:
                self.set_status("Moved tile.")
        else:
            self.set_status("Click an adjacent tile to the blank to move.")

# ---------- Run the app ----------

def main():
    root = tk.Tk()
    app = PuzzleApp(root)
    root.geometry("900x700")
    root.mainloop()

if _name_ == "_main_":
    main()

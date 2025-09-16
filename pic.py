"""
concept_puzzle_app_fast.py

Tkinter app:
- Generate an instant placeholder image from a text concept.
- Convert image into sliding puzzle (NxN), shuffle, and allow play.
- No API calls, so it loads instantly.
"""

import os
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont

# ---------- FAST PLACEHOLDER IMAGE CREATION ----------
def make_placeholder_image(prompt, size=(512, 512)):
    """Instant placeholder image with prompt text."""
    w, h = size
    img = Image.new("RGB", (w, h), (240, 245, 255))
    draw = ImageDraw.Draw(img)

    # add some decorative shapes
    for _ in range(12):
        x0, y0 = random.randint(0, w-100), random.randint(0, h-100)
        x1, y1 = x0 + random.randint(50, 200), y0 + random.randint(50, 200)
        color = (
            random.randint(100, 220),
            random.randint(100, 220),
            random.randint(100, 220)
        )
        draw.ellipse([x0, y0, x1, y1], fill=color)

    # add the prompt text
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
    # blank tile
    blank = Image.new("RGB", (tile_w, tile_h), (200, 200, 200))
    tiles[-1] = blank
    return tiles

def make_random_permutation(n_tiles):
    perm = list(range(n_tiles))
    random.shuffle(perm)
    return perm

# ---------- Tkinter UI & Game ----------
class PuzzleApp:
    def _init_(self, root):
        self.root = root
        root.title("Concept → Puzzle (Fast)")
        self.image = None
        self.tiles = None
        self.grid_size = 3
        self.tile_imgs_tk = []
        self.current_perm = None
        self.blank_pos = None
        self.tile_buttons = []

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
        self.prompt_var = tk.StringVar(value="A sunny day at the beach")
        self.prompt_entry = ttk.Entry(top, textvariable=self.prompt_var, width=50)
        self.prompt_entry.grid(row=0, column=1, padx=6, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Button(top, text="Generate Image", command=self.on_generate).grid(row=0, column=2, padx=6)
        ttk.Button(top, text="Save Image...", command=self.on_save_image).grid(row=0, column=3, padx=6)

        # puzzle controls
        pctrl = ttk.Frame(frm)
        pctrl.grid(row=1, column=0, sticky="ew", pady=(8,6))
        ttk.Label(pctrl, text="Grid size:").grid(row=0, column=0, sticky="w")
        self.grid_var = tk.IntVar(value=3)
        grid_spin = ttk.Spinbox(pctrl, from_=2, to=6, textvariable=self.grid_var, width=4)
        grid_spin.grid(row=0, column=1, padx=6, sticky="w")

        ttk.Button(pctrl, text="Create Puzzle", command=self.on_create_puzzle).grid(row=0, column=2, padx=8)
        ttk.Button(pctrl, text="Shuffle", command=self.on_shuffle).grid(row=0, column=3, padx=4)
        ttk.Button(pctrl, text="Reset", command=self.on_reset).grid(row=0, column=4, padx=4)

        # board
        board_frame = ttk.Frame(frm, borderwidth=2, relief="sunken")
        board_frame.grid(row=2, column=0, sticky="nsew")
        frm.rowconfigure(2, weight=1)
        self.board_frame = board_frame
        self.board_canvas = ttk.Frame(board_frame)
        self.board_canvas.pack(expand=True, fill="both", padx=4, pady=4)

        # status
        self.status_var = tk.StringVar(value="No image yet.")
        ttk.Label(frm, textvariable=self.status_var).grid(row=3, column=0, sticky="we", pady=(6,0))

    def set_status(self, txt):
        self.status_var.set(txt)

    def on_generate(self):
        prompt = self.prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning("Empty prompt", "Please enter a concept first.")
            return
        self.image = make_placeholder_image(prompt, size=(512,512))
        self.set_status("Instant placeholder image created.")
        self.show_image_preview()
        self.on_create_puzzle()

    def on_save_image(self):
        if not self.image:
            messagebox.showinfo("No image", "No image to save.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG image","*.png")])
        if path:
            self.image.save(path)
            self.set_status(f"Image saved to {path}")

    def show_image_preview(self):
        for child in self.board_canvas.winfo_children():
            child.destroy()
        if not self.image:
            return
        preview = self.image.copy()
        preview.thumbnail((240,240))
        self.preview_tk = ImageTk.PhotoImage(preview)
        lbl = ttk.Label(self.board_canvas, image=self.preview_tk)
        lbl.pack(padx=8, pady=8)

    def on_create_puzzle(self):
        if not self.image:
            messagebox.showinfo("No image", "Please generate an image first.")
            return
        n = int(self.grid_var.get())
        if n < 2 or n > 6:
            messagebox.showwarning("Grid size", "Grid size must be between 2 and 6.")
            return
        self.grid_size = n
        # resize image to square
        side = min(self.image.size)
        img_cropped = self.image.crop(((self.image.size[0]-side)//2,
                                       (self.image.size[1]-side)//2,
                                       (self.image.size[0]+side)//2,
                                       (self.image.size[1]+side)//2))
        img_resized = img_cropped.resize((n*128, n*128))
        self.tiles = split_image_to_tiles(img_resized, n)
        self.n_tiles = len(self.tiles)
        self.current_perm = make_random_permutation(self.n_tiles)
        self.blank_pos = self.current_perm.index(self.n_tiles-1)
        self.render_tiles()
        self.set_status(f"Puzzle created: {n}x{n}")

    def on_shuffle(self):
        if not self.tiles: return
        self.current_perm = make_random_permutation(self.n_tiles)
        self.blank_pos = self.current_perm.index(self.n_tiles-1)
        self.render_tiles()
        self.set_status("Shuffled puzzle.")

    def on_reset(self):
        if not self.tiles: return
        self.current_perm = list(range(self.n_tiles))
        self.blank_pos = self.n_tiles-1
        self.render_tiles()
        self.set_status("Reset to solved state.")

    def render_tiles(self):
        for child in self.board_canvas.winfo_children():
            child.destroy()
        n = self.grid_size
        self.tile_imgs_tk = []
        for pos in range(self.n_tiles):
            tile_idx = self.current_perm[pos]
            pil_tile = self.tiles[tile_idx]
            tkimg = ImageTk.PhotoImage(pil_tile)
            self.tile_imgs_tk.append(tkimg)
            btn = ttk.Button(self.board_canvas, image=tkimg,
                             command=lambda p=pos: self.on_tile_click(p))
            btn.grid(row=pos//n, column=pos%n)
        self.board_canvas.update()

    def on_tile_click(self, pos):
        n = self.grid_size
        r, c = pos//n, pos%n
        br, bc = self.blank_pos//n, self.blank_pos%n
        if (abs(r-br)==1 and c==bc) or (abs(c-bc)==1 and r==br):
            self.current_perm[self.blank_pos], self.current_perm[pos] = \
                self.current_perm[pos], self.current_perm[self.blank_pos]
            self.blank_pos = pos
            self.render_tiles()
            if self.current_perm == list(range(self.n_tiles)):
                self.set_status("Solved! 🎉")
                messagebox.showinfo("Congratulations", "You solved the puzzle!")

# ---------- Run the app ----------
def main():
    root = tk.Tk()
    app = PuzzleApp(root)
    root.geometry("800x700")
    root.mainloop()

if __name__ == "_main_":
    main()

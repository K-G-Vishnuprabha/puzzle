import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import random
from io import BytesIO
import os
import time
import requests


try:
    from google import genai
    from google.genai import types   
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

API_KEY ="AIzaSyC-M67oE4cgOIXqjabD-emkOrS6WTwowVw"

if GEMINI_AVAILABLE:
    
    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(api_version="v1")
    )


def generate_gemini_image(prompt: str) -> Image.Image:
    """Generate an image using AI or fallback random image."""
    try:
        if GEMINI_AVAILABLE:
            response = client.models.generate_images(
                model="gemini-3-flash-preview",
                prompt=prompt
            )

            img_bytes = response.generated_images[0].image.image_bytes
            return Image.open(BytesIO(img_bytes))

    except Exception as e:
        print("AI image generation failed:", e)

    # fallback image
    try:
        url = "https://picsum.photos/400"
        img_bytes = requests.get(url).content
        return Image.open(BytesIO(img_bytes))
    except:
        return Image.new("RGB", (400, 400), "gray")


class PuzzleApp:
    def __init__(self, root, image: Image.Image, grid_size=3, player="Player"):
        self.root = root
        self.grid_size = grid_size
        self.original_image = image.copy()
        self.image = image
        self.player = player
        self.pieces = []
        self.tiles = []
        self.buttons = []
        self.selected_tile = None
        self.moves = 0
        self.start_time = time.time()

        self.prepare_puzzle()
        self.create_ui()

    def prepare_puzzle(self):
        self.image = self.image.resize((400, 400))
        w, h = self.image.size
        pw, ph = w // self.grid_size, h // self.grid_size

        for i in range(self.grid_size):
            for j in range(self.grid_size):
                piece = self.image.crop((j * pw, i * ph, (j + 1) * pw, (i + 1) * ph))
                self.pieces.append(ImageTk.PhotoImage(piece))

        self.tiles = list(range(len(self.pieces)))
        random.shuffle(self.tiles)

    def create_ui(self):
        frame = tk.Frame(self.root, bg="black")
        frame.pack(pady=20)

        index = 0
        for i in range(self.grid_size):
            row = []
            for j in range(self.grid_size):
                btn = tk.Button(frame, image=self.pieces[self.tiles[index]],
                                command=lambda i=i, j=j: self.on_click(i, j))
                btn.grid(row=i, column=j, padx=2, pady=2)
                row.append(btn)
                index += 1
            self.buttons.append(row)

        self.info_label = tk.Label(self.root, text=f"Moves: 0 | Time: 0s",
                                   font=("Arial", 12, "bold"), bg="black", fg="white")
        self.info_label.pack(pady=10)

        self.hint_button = tk.Button(self.root, text="🔍 Show Hint (Penalty +5 moves)",
                                     command=self.show_original)
        self.hint_button.pack(pady=5)

        self.update_timer()

    def update_timer(self):
        elapsed = int(time.time() - self.start_time)
        self.info_label.config(text=f"Moves: {self.moves} | Time: {elapsed}s")
        self.root.after(1000, self.update_timer)

    def on_click(self, i, j):
        idx = i * self.grid_size + j
        if self.selected_tile is None:
            self.selected_tile = idx
        else:
            self.tiles[self.selected_tile], self.tiles[idx] = self.tiles[idx], self.tiles[self.selected_tile]
            self.moves += 1
            self.update_board()
            self.selected_tile = None
            if self.check_win():
                self.on_win()

    def update_board(self):
        index = 0
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                self.buttons[i][j].config(image=self.pieces[self.tiles[index]])
                index += 1

    def check_win(self):
        return all(i == tile for i, tile in enumerate(self.tiles))

    def show_original(self):
        self.moves += 5
        self.update_timer()

        top = tk.Toplevel(self.root)
        top.title("Original Image (Hint)")

        top.transient(self.root)
        top.grab_set()

        preview = self.original_image.resize((300, 300))
        img_preview = ImageTk.PhotoImage(preview)
        lbl = tk.Label(top, image=img_preview)
        lbl.image = img_preview
        lbl.pack()

        tk.Label(top, text="Hint Used (+5 Moves)", fg="red").pack()
        tk.Button(top, text="Close", command=top.destroy).pack(pady=5)

        def on_close():
            top.grab_release()
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", on_close)

    def calculate_score(self, elapsed):
        raw_score = max(0, 10000 - ((self.moves * 20) + (elapsed * 10)))
        score_out_of_10 = round((raw_score / 10000) * 10, 1)
        return score_out_of_10

    def on_win(self):
        elapsed = int(time.time() - self.start_time)
        score = self.calculate_score(elapsed)

        win_top = tk.Toplevel(self.root)
        win_top.title("🎉 Puzzle Solved!")

        tk.Label(win_top, text=f"Congrats {self.player}!",
                 font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(win_top, text=f"Moves: {self.moves} | Time: {elapsed}s",
                 font=("Arial", 12)).pack(pady=5)
        tk.Label(win_top, text=f"Score: {score}",
                 font=("Arial", 12, "bold"), fg="green").pack(pady=5)

        preview = self.original_image.resize((300, 300))
        img_preview = ImageTk.PhotoImage(preview)
        lbl = tk.Label(win_top, image=img_preview)
        lbl.image = img_preview
        lbl.pack(pady=10)

        with open("leaderboard.txt", "a") as f:
            f.write(f"{self.player},{self.grid_size}x{self.grid_size},{self.moves},{elapsed},{score}\n")

        tk.Button(win_top, text="Play Again", command=lambda: [self.root.destroy(), win_top.destroy(), main()]).pack(pady=10)


def main():
    root = tk.Tk()
    root.title("⚡ TechFest Puzzle Game ⚡")
    root.geometry("500x600")
    root.configure(bg="black")

    tk.Label(root, text="⚡ Welcome to TechFest Puzzle Game ⚡",
             font=("Arial", 16, "bold"), fg="cyan", bg="black").pack(pady=20)

    tk.Label(root, text="Rules:\n1. Enter a prompt to generate an image.\n"
                        "2. Solve the puzzle as fast as you can!\n"
                        "3. Each hint adds +5 moves penalty.\n"
                        "4. Game is paused while hint is visible.",
             font=("Arial", 12), fg="white", bg="black").pack(pady=10)

    player = simpledialog.askstring("Player Name", "Enter your name:")
    if not player:
        player = "Guest"

    prompt = simpledialog.askstring("Image Prompt", "Enter a prompt for your puzzle image:")
    if not prompt:
        prompt = "Colorful abstract pattern"

    try:
        img = generate_gemini_image(prompt)
    except Exception as e:
        print(e)
        img = Image.new("RGB", (400, 400), "gray")

    def start_game(size):
        root.destroy()
        game_root = tk.Tk()
        game_root.title("TechFest Puzzle Game")
        PuzzleApp(game_root, img, grid_size=size, player=player)
        game_root.mainloop()

    tk.Button(root, text="Easy (3x3)", font=("Arial", 12, "bold"),
              command=lambda: start_game(3)).pack(pady=10)
    tk.Button(root, text="Medium (4x4)", font=("Arial", 12, "bold"),
              command=lambda: start_game(4)).pack(pady=10)
    tk.Button(root, text="Hard (5x5)", font=("Arial", 12, "bold"),
              command=lambda: start_game(5)).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()

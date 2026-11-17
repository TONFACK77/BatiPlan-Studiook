"""Generates the product logo / icon (own artwork)."""
from PIL import Image, ImageDraw
import os
S = 1024; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
d.rounded_rectangle((0, 0, S, S), radius=190, fill=(24, 54, 94, 255)); w = 64; col = (255, 255, 255, 255)
d.rectangle((190, 250, 834, 774), outline=col, width=w); d.rectangle((510, 250, 510 + w, 560), fill=col); d.rectangle((190, 560, 640, 560 + w), fill=col)
d.rectangle((300, 768, 460, 774 + w), fill=(24, 54, 94, 255)); d.arc((140, 614, 460, 934), 270, 360, fill=(255, 190, 70, 255), width=22); d.line((300, 806, 300, 646), fill=(255, 190, 70, 255), width=22)
d.rectangle((640, 246, 800, 250 + w + 4), fill=(24, 54, 94, 255)); d.line((640, 278, 800, 278), fill=(120, 200, 255, 255), width=14); d.line((640, 288, 800, 288), fill=(120, 200, 255, 255), width=14)
os.makedirs("assets", exist_ok=True); im.save("assets/logo.png"); im.resize((256, 256), Image.LANCZOS).save("assets/icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]); print("logo ok")

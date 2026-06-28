from PIL import Image
import zlib
import base64

img = Image.open("bird.png").convert("RGB")

raw = img.tobytes()

compressed = zlib.compress(raw)

bird = base64.a85encode(compressed, adobe=True)
bird = bird.decode()
print(bird)
print(len(bird))

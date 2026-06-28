from PIL import Image

img = Image.open("cloud.png").convert("RGBA")

datas = [
    (255, 255, 255, 255) if pixel[:3] != (0, 0, 0)
    else (0, 0, 0, 0)
    for pixel in img.getdata()
]

img.putdata(datas)
img.save("cloud_transparent.png")
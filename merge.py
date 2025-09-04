from PIL import Image

# Load your PNG
img = Image.open("Club_logo_smaller-removebg-preview.png")

# Define sizes Windows uses for taskbar / titlebar
sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]

# Save multi-size ICO
img.save("Club_logo.ico", sizes=sizes)

from PIL import Image, ImageDraw

def create_icons():
    # 256x256 for high quality on taskbar
    size = 256
    # Use transparent background (RGBA) to ensure it's just a dot!
    image = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a red circle (dot) in the center
    margin = 40 # Smaller margin for a bigger dot
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(239, 68, 68, 255))
    
    # Save as PNG
    image.save('app_icon.png')
    # Save as ICO (Windows taskbar prefers this)
    image.save('app_icon.ico', format='ICO', sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
    print("Minimalist red dot icons created: app_icon.png and app_icon.ico")

if __name__ == "__main__":
    create_icons()

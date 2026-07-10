import os
import colorsys
from PIL import Image

def generate_color_blocks(output_dir, num_colors=128):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for i in range(num_colors):
        # Scale hue evenly from 0.0 to 1.0
        hue = i / num_colors
        # Generate vibrant colors (90% saturation and brightness)
        r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 0.9)
        rgb_color = (int(r * 255), int(g * 255), int(b * 255))
        
        img = Image.new('RGB', (200, 200), color=rgb_color)
        img.save(os.path.join(output_dir, f"color_block_{i}.jpg"))
        
if __name__ == "__main__":
    generate_color_blocks(r"D:\MainProject\PhotoMontage\element_img")
    print("Generated 128 test images distributed across the color spectrum.")


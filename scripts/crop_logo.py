from PIL import Image
import os

def crop_image(file_path):
    try:
        img = Image.open(file_path)
        img = img.convert("RGBA")
        
        print(f"Corner pixel (0,0): {img.getpixel((0,0))}")
        print(f"Corner pixel (w-1,h-1): {img.getpixel((img.width-1, img.height-1))}")
        
        datas = img.getdata()
        
        newData = []
        count_transparent = 0
        for item in datas:
            # Change all white (also shades of whites)
            # to transparent
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                newData.append((255, 255, 255, 0))
                count_transparent += 1
            else:
                newData.append(item)
        
        print(f"Made {count_transparent} pixels transparent out of {len(datas)}")
        
        img.putdata(newData)
        
        # Now get bbox of non-transparent
        bbox = img.getbbox()
        
        if bbox:
            cropped_img = img.crop(bbox)
            cropped_img.save(file_path)
            print(f"Successfully cropped {file_path}")
            print(f"Original size: {img.size}, New size: {cropped_img.size}")
            print(f"BBox: {bbox}")
        else:
            print("Image is empty or transparent, nothing to crop.")
            
    except Exception as e:
        print(f"Error cropping image: {e}")

if __name__ == "__main__":
    logo_path = r"c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\src\frontend\src\assets\official_logo.png"
    if os.path.exists(logo_path):
        crop_image(logo_path)
    else:
        print(f"File not found: {logo_path}")

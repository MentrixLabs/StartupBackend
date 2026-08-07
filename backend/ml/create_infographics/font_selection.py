import json

with open('assets/fonts_angles.json') as f:
    fonts_data = json.load(f)

def find_closest_font(target_ratio):
    closest_font = None
    min_diff = float('inf')
    
    for font in fonts_data['fonts']:
        diff = abs(font['ratio'] - target_ratio)
        if diff < min_diff:
            min_diff = diff
            closest_font = font
    return closest_font

if __name__ == "__main__":
    best_font = find_closest_font(0.8)
    print(f"Рекомендуемый шрифт: {best_font['name']} ({best_font['type']})")

from create_infographics import create_infographics, load_image, save_image
#from ..seo.tri import product_properties

if __name__ == '__main__':
    image_path = './example/AP6500E(4).png'
    background_path = './example/bac.jpg'

    # Слайды объединять в одну строку с переносом текста "\n"
    description = [f"""Apple iPhone 16 Pro Max
                    Apple iPhone 16 Pro Max
                    Дисплей: 6.9" OLED - 1320 x 2868
                    Чип: Apple A18 Pro
                    Камера: 4 (48 MP + 12 MP + 48 MP)
                    Батарея: 4685 мАч
                    OS: iOS 18.5
                    Вес: 227 г."""]
    #texts = product_properties(description)

    # ! Загружается через PIL (картинки PIL и cv2 отличаются, их нужно преобразовывать)
    image = load_image(image_path)

    result = create_infographics(image, description)
    
    save_image(result, './example/output.png')

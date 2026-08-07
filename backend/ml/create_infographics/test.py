import cv2
import numpy as np

from create_infographics import create_infographics, load_image, save_image

if __name__ == '__main__':
    image_path = "./example/AP6500E(4).png"
    background_path = "./example/back_for_gen.jpg"
    font_path = "./assets/Jaro_Cyrillic/jaro-cyrillic.otf"

    slides = [
        ["Готовы Работать Без Ограничений?",
        "Мощность: 6.5 кВт (максимальная) / 5.8 кВт",
        "Двигатель: OHV, 4-тактный, воздушное охлаждение",
        "Розетки: 1x 220В 16А, 1x 12В DC",
        "Время работы: ~X часов при 50% нагрузке",
        "Мощности хватит на бетономешалку + перфоратор + освещение; сварочный инвертор; звуковое оборудование"],
        ["Почему AP6500E Становится Вашим Незаменимым Помощником?",
        "Надежность 24/7: Мощный двигатель OHV, защита от перегрузок. Ваша работа без сбоев.",
        "Оптимизированный расход. Меньше трат на бензин, больше работы.",
        "Легкий доступ к ключевым узлам. Экономия вашего времени и денег.",
        "Компактные размеры, колеса (если есть). Энергия там, где она нужна Вам."],
        ["AP6500E Работает Для Вас Где Угодно! От стройки до пикника",
        "Остались Вопросы? Пишите",
        "Выбирайте надежность. Выбирайте AP6500E!"]
    ]

    for number, slide in enumerate(slides):
        image = load_image(image_path)
        background = load_image(background_path)

        result = create_infographics(image, slide, number, image_background=background, need_mask=False, font_path=font_path)
        
        save_image(result, "slides")
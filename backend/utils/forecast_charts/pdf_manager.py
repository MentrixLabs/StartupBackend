import io
from datetime import datetime

from PIL import Image, ImageDraw
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from pathlib import Path
from reportlab.pdfgen import canvas

from utils.data_converter.date_converter import format_date
from utils.forecast_charts.forecast_manager import ForeсastManager

class PDFManager:
    current_dir = Path(__file__).resolve().parent
    PAGE_WIDTH, PAGE_HEIGHT = A4

    @staticmethod
    def draw_border(c):
        """Рисует рамку вокруг страницы"""
        margin = 10 
        c.setStrokeColorRGB(0.1, 0.1, 0.1)  
        c.setLineWidth(2) 
        c.rect(margin, margin, PDFManager.PAGE_WIDTH - 2 * margin, PDFManager.PAGE_HEIGHT - 2 * margin)
        

    @staticmethod
    def make_rounded_logo_on_white(png_path: Path, radius: int = 250):
        """Обрабатывает изображение, добавляя закруглённые края и белый фон"""
        with Image.open(png_path).convert("RGBA") as img:
            size = min(img.size)
            img = img.resize((size, size), Image.LANCZOS)

            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)

            rounded = Image.new("RGBA", (size, size))
            rounded.paste(img, (0, 0), mask=mask)

            white_bg = Image.new("RGB", (size, size), (255, 255, 255))
            white_bg.paste(rounded, (0, 0), mask=mask)

            output = io.BytesIO()
            white_bg.save(output, format="PNG")
            output.seek(0)
            return output
        
    @staticmethod
    def draw_multiline_centered_string(c, x_center, y_start, text, max_words_per_line=4, line_height=30, font_name="Geoform", font_size=30):
        c.setFont(font_name, font_size)
        words = text.split()
        lines = [ " ".join(words[i:i+max_words_per_line]) for i in range(0, len(words), max_words_per_line) ]

        y = y_start
        for line in lines:
            c.drawCentredString(x_center, y, line)
            y -= line_height    
        
    @staticmethod
    def generate_pdf(predictions_data, product_data):
        """"Генерирует PDF-документ с прогнозами возвращая буфер"""
        current_dir = PDFManager.current_dir
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)

        pdfmetrics.registerFont(TTFont('Geoform', str(current_dir / "fonts" / "ru_Geoform.ttf")))
        c.setFont("Geoform", 24)
        PDFManager.draw_border(c)
        image_path = PDFManager.make_rounded_logo_on_white(current_dir / "logos" / "logo1.jpg")
        c.drawImage(ImageReader(image_path), (PDFManager.PAGE_WIDTH - 100) / 2, PDFManager.PAGE_HEIGHT - 150, width=100, height=100)
        c.setFont("Geoform", 30)
        PDFManager.draw_multiline_centered_string(
            c,
            PDFManager.PAGE_WIDTH / 2,
            PDFManager.PAGE_HEIGHT - 230,
            f"Прогноз товара:\n\n«{product_data.cardname}»",
            max_words_per_line=3,
            line_height=35,
            font_name="Geoform",
            font_size=25,
        )
        c.setFont("Geoform", 18)
        c.drawCentredString(PDFManager.PAGE_WIDTH / 2, PDFManager.PAGE_HEIGHT - 600, "PROSKlad")
        c.setFont("Geoform", 12)
        c.drawCentredString(PDFManager.PAGE_WIDTH / 2, 40, f"от {format_date(datetime.today())}")
        c.showPage()

        plots, days_left = ForeсastManager.generate_all_forecasts(predictions_data)

        for plot in plots:
            c.drawImage(ImageReader(plot), 0, 0, width=PDFManager.PAGE_WIDTH, height=PDFManager.PAGE_HEIGHT - 50)
            c.showPage()

        c.setFont("Geoform", 16)
        PDFManager.draw_border(c)
        text = c.beginText(PDFManager.PAGE_WIDTH / 6, PDFManager.PAGE_HEIGHT / 1.1  )
        text.setFont("Geoform", 16)
        
        text_lines = [
            f"Дней до OOS: {days_left}.",
            "...",
        ]
        
        for line in text_lines:
            text.textLine(line)

        c.drawText(text)
        c.save()

        pdf_buffer.seek(0)
        return pdf_buffer

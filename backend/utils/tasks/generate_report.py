import os
import asyncio
import asyncpg

from db.ozon.dao import OzonItemsDAO
from ml.remainder_prediction.model import prediction_days_json
from utils.celery.celery_app import celery
from utils.forecast_charts.pdf_manager import PDFManager
from config import settings


@celery.task(name="utils.tasks.generate_report.generate_daily_reports",
             bind=True, max_retries=3, acks_late=True)
def generate_daily_reports(self):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(_generate_daily_reports())
        return result
    except Exception as e:
        print(f"Error in task: {e}")
        raise self.retry(exc=e)

async def _generate_daily_reports():
    try:
        conn = await asyncpg.connect(
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            host=settings.DB_HOST,
        )
        
        try:
            products = await OzonItemsDAO.find_all()
            
            if not products:
                print("No products found")
                return None

            os.makedirs("reports", exist_ok=True)

            for card in products:
                try:
                    data_to_model = {
                        "category": card.category,
                        "dates": list(card.dates) if card.dates else [],
                        "prices": list(card.prices) if card.prices else [],
                        "counts": list(card.fbs_count) if card.fbs_count else [],
                    }

                    predictions_data = prediction_days_json(data_to_model, days=7)
                    pdf_buffer = PDFManager.generate_pdf(predictions_data, card)

                    report_path = f"reports/report_{card.id}.pdf"
                    with open(report_path, "wb") as f:
                        f.write(pdf_buffer.getbuffer())
                    
                    print(f"Successfully generated report for product {card.id}")

                except Exception as e:
                    print(f"Error processing card {card.id}: {e}")
                    continue

            return "Reports generated successfully"
        finally:
            await conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        raise
    
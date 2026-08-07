import io

from datetime import datetime
from pathlib import Path 

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from utils.data_converter.date_converter import format_date


class ForeсastManager:
    current_dir = Path(__file__).resolve().parent
    
    @staticmethod
    def generate_all_forecasts(predictions_data):
        """Генерация всех графиков прогнозов по данным ML"""
        
        matplotlib.use('Agg')
        data = predictions_data
        
        min_len = min(len(data['counts']), len(data['prices']), len(data['dates']))
        x = [format_date(datetime.strptime(d, "%Y-%m-%d")) for d in data['dates'][:min_len]]
        counts = data['counts'][:min_len]
        price = data['prices'][:min_len]

        font_path = ForeсastManager.current_dir / "fonts" / "ru_Geoform.ttf"
        fm.fontManager.addfont(str(font_path))
        font_prop = fm.FontProperties(fname=font_path)  

        plt.rcParams['font.family'] = font_prop.get_name()
    
        plots = []
        for series, label, color in [
            (counts, "Остатки", "#7F8C8D"),
            (price, "Цена", "#A93226"),
        ]:
            buf = io.BytesIO()
            plt.figure(figsize=(8.27, 11.69), facecolor='white')
            plt.plot(x, series, marker='o', linestyle='-', color=color, linewidth=2, label=label)
            plt.title(f'{label} по дням', fontsize=14, color=color)
            plt.xlabel('Дата')
            plt.ylabel(label)
            plt.xticks(rotation=90, fontsize=7)
            plt.yticks(fontsize=8)
            plt.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
            plt.tight_layout()
            plt.legend(loc="upper right", fontsize=9)
            plt.savefig(buf, format='PNG', dpi=300, bbox_inches='tight')
            plt.close()
            buf.seek(0)
            plots.append(buf)
            
        days_left = max(len(price) - price.index(min(price)), 0)
        return plots, days_left
    

import json
import os
import numpy as np
import pandas as pd

def csv_chunks(input_csv, chunk_size=100_000):
    return pd.read_csv(input_csv, chunksize=chunk_size, compression='gzip')

def list_categories(input_chunks):
    '''Выводит список категорий и количество уникальных товаров в них'''
    categories_products = {}

    for chunk in input_chunks:
        chunk = chunk.dropna(subset=['category_code'])

        for cat, grp in chunk.groupby('category_code'):
            prod_ids = grp['product_id'].unique()
            if cat not in categories_products:
                categories_products[cat] = set()
            categories_products[cat].update(prod_ids)

    category_counts = {cat: len(products) for cat, products in categories_products.items()}
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_categories

def accumulate_events(df: pd.DataFrame) -> pd.DataFrame:
    '''Обрабатывает события покупок, агрегируя по дате и цене'''
    df = df.copy()

    df['event_time'] = pd.to_datetime(df['event_time'], utc=True, errors='coerce')
    df = df[df['event_type'] == 'purchase'].copy()

    df['category_code'] = df['category_code'].fillna('')
    df['brand'] = df['brand'].fillna('')

    df['date'] = df['event_time'].dt.date

    grouped = df.groupby(['product_id', 'date', 'price'], as_index=False)
    agg = grouped.agg(
        count=('event_type', 'count'),
        category=('category_code', 'first'),
        brand=('brand', 'first'),
        last_time=('event_time', 'max')
    )

    agg['datetime'] = agg['last_time'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')

    return agg[['product_id', 'category', 'brand', 'datetime', 'price', 'count']]

def build_sequences(df: pd.DataFrame) -> list:
    '''Строит последовательности покупок по дням для каждого продукта с агрегацией по дате и цене'''
    products = []

    df['datetime'] = pd.to_datetime(df['datetime'].str.replace(' UTC', ''), format='%Y-%m-%d %H:%M:%S')

    for pid, grp in df.groupby('product_id'):
        grp['date'] = grp['datetime'].dt.date

        grouped = grp.groupby(['date', 'price'], as_index=False).agg({
            'count': 'sum',
            'category': 'first',
            'brand': 'first',
            'datetime': 'max'
        })

        grouped = grouped.sort_values('datetime')

        products.append({
            'product_id': int(pid),
            'category': grouped['category'].iloc[0] if not grouped['category'].isnull().all() else '',
            'brand': grouped['brand'].iloc[0] if not grouped['brand'].isnull().all() else '',
            'dates': grouped['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S UTC').tolist(),
            'prices': [float(x) for x in grouped['price']],
            'counts': [int(x) for x in grouped['count']]
        })

    return products

def save_json(data: list, output_dir: str, per_file=10000):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(0, len(data), per_file):
        chunk = data[i:i+per_file]
        fname = os.path.join(output_dir, f'products_{i//per_file}.jsonl')
        with open(fname, 'w') as f:
            for item in chunk:
                json.dump(item, f)
                f.write('\n')

def process_data(input_chunks, output_dir: str, chunk_size=100000):
    '''Основной процесс обработки: читаем чанки, агрегируем и сохраняем'''
    chunks = []
    for chunk in input_chunks:
        processed = accumulate_events(chunk)
        chunks.append(processed)

    final_df = pd.concat(chunks, ignore_index=True)
    final_df = final_df.groupby(['product_id', 'datetime', 'price'], as_index=False).agg({
        'count': 'sum',
        'category': 'first',
        'brand': 'first'
    })

    products_data = build_sequences(final_df)
    save_json(products_data, output_dir)
    print(f'Обработано {len(products_data)} продуктов. Данные сохранены в {output_dir}')


def open_jsonl(directories):
    products = []
    
    if isinstance(directories, str):
        directories = [directories]

    for directory in directories:
        for jsonl_file in os.listdir(directory):
            with open(os.path.join(directory, jsonl_file), 'r') as json_file:
                products.extend([json.loads(line) for line in json_file])
    return products

def merge_duplicate_products(data):
    '''объединяет данные о товаре в list products'''
    merged = {}
    
    for product in data:
        pid = product["product_id"]
        
        if pid in merged:
            merged[pid]["dates"].extend(product["dates"])
            merged[pid]["prices"].extend(product["prices"])
            merged[pid]["counts"].extend(product["counts"])
        else:
            merged[pid] = {
                "product_id": pid,
                "category": product["category"],
                "brand": product["brand"],
                "dates": product["dates"].copy(),
                "prices": product["prices"].copy(),
                "counts": product["counts"].copy()
            }
    
    return list(merged.values())

def create_dataset_csv(path_csv='data.csv', output_csv='output.csv', verbose=1):
    df = pd.read_csv(path_csv, dtype={'category': str}, low_memory=False)
    df['category'] = df['category'].fillna('other')
    df['dates'] = pd.to_datetime(df['dates'])
    
    median_prices = df[df['counts'] > 0].groupby('category')['prices'].median()
    
    min_date, max_date = df['dates'].min(), df['dates'].max()
    all_dates = pd.date_range(min_date, max_date, freq='D')
    categories = df['category'].unique()
    
    grouped = df.groupby(['category', 'dates'])[['counts', 'prices']].mean()
    
    multi_index = pd.MultiIndex.from_product(
        [categories, all_dates],
        names=['category', 'dates']
    )
    result = grouped.reindex(multi_index, fill_value=0).reset_index()
    
    for category in categories:
        mask = (result['category'] == category) & (result['counts'] == 0)
        result.loc[mask, 'prices'] = median_prices.get(category, 0)
    
    result.to_csv(output_csv, index=False)
    
    if verbose == 1:
        print(f"Уникальных категорий: {len(categories)}")
        print("Пример данных:")
        print(result.head())
        print("\nПример заполненных цен для дней без продаж:")
        print(result[(result['counts'] == 0) & (result['prices'] > 0)].head())

if __name__ == '__main__':
    # ! Занимает много времени и ресурсов компа

    # 1 обработка
    files = ['2019-Oct', '2019-Nov', '2019-Dec', '2020-Jan', '2020-Feb', '2020-Mar', '2020-Apr']
    for file in files:
        chunks = csv_chunks(f'data/{file}.csv.gz')
        process_data(chunks, f'data/{file}')

    # 2 обработка
    directories = ['2019-Oct', '2019-Nov', '2019-Dec', '2020-Jan', '2020-Feb', '2020-Mar', '2020-Apr']
    directories = [f'data/{directory}' for directory in directories]
    products = open_jsonl(directories)
    products = merge_duplicate_products(products)
    products.sort(key=lambda product: product['product_id'])
    save_json(products, 'data/dataset')
    print(products[:5])

    # 3 образотка
    directory = 'data/dataset-remainder-prediction/'
    products = open_jsonl(directory)
    df = pd.DataFrame(products)
    df = df.explode(['dates', 'prices', 'counts'], ignore_index=True)
    df['dates'] = pd.to_datetime(df['dates'])
    df = df.sort_values(by=['brand', 'category', 'product_id', 'dates'])
    df['dates'] = pd.to_datetime(df['dates']).dt.strftime('%Y-%m-%d')
    df.to_csv('./data.csv')

    # 4 образотка
    create_dataset_csv()

    # датасет готов в 'output.csv'

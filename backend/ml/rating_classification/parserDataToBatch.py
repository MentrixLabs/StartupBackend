import os
import json

def process_batch(parser_directory, batch_size = 500, output_directory = 'dataset/description', verbose=1):
    os.makedirs(output_directory, exist_ok=True)

    if verbose == 1: print('Поиск всех элементов parser')

    parser_path_items = os.listdir(parser_directory)

    if verbose == 1: print(f'Найдено {len(parser_path_items)} элементов')

    batch_count = 0

    for batch_num, i in enumerate(range(0, len(parser_path_items), batch_size), 1):
        batch_files = parser_path_items[i:i + batch_size]
        batch_data = []
        
        for file_item in batch_files:
            json_path = os.path.join(parser_directory, file_item, 'product_data.json')
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    batch_data.append(json.load(f))
            except:
                if verbose == 1: print(f'Файл {json_path} не существует')
        
        output_path = os.path.join(output_directory, f"batch_{batch_num}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"products": batch_data}, f, indent=2, ensure_ascii=False)
        
        batch_count += 1
        
        if verbose == 1: print(f'Сохранено {output_path}')

    if verbose == 1: print(f'Сохранено {batch_count} батчей')

    return batch_count

if __name__ == '__main__':
    # Путь до parser data
    folder_path = 'ozon_data/ozon_data'
    batch_count = process_batch(folder_path, batch_size=1000, output_directory='dataset/description')

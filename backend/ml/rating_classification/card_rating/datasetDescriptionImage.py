import os
import json
from pathlib import Path
from PIL import Image

import numpy as np
import matplotlib.pyplot as plt
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms



class ProductDataset(Dataset):
    def __init__(self, root_dir, title_key="title", transform=None):
        self.samples = []
        self.transform = transform
        root = Path(root_dir)

        for sub in root.iterdir():
            if not sub.is_dir():
                continue
            img_path = sub / "image_1.webp"
            json_path = sub / "product_data.json"
            if img_path.exists() and json_path.exists():
                data = json.loads(json_path.read_text(encoding="utf-8"))
                desc = data.get("product_data", "").get(title_key, "").strip()
                if desc:
                    self.samples.append((img_path, desc))

        if not self.samples:
            raise ValueError(f"Не найдено ни одного валидного примера в {root_dir}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, caption = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, caption


def main():
    data_path = "C:/Users/Alexey Balakin/Desktop/ozon_data_test" # На проде надо поменять

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])

    dataset = ProductDataset(data_path, title_key="title", transform=transform)
    loader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=4)


    for batch in loader:
        images, captions = batch
        for i in range(min(5, len(captions))):
            print(f"[{i}] Caption: {captions[i]}")
            print(f"Image tensor shape: {images[i].shape}",)
            img = images[i].numpy().transpose((1, 2, 0))
            plt.imshow(img)
            plt.title(captions[i])
            plt.axis('off')
            plt.show()
            print("-" * 40)
        break  # Только первый батч


if __name__ == '__main__':
    main()
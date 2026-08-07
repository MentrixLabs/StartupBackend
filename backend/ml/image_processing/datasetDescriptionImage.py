import os
import json
from pathlib import Path
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence
import torchvision.transforms as T
import spacy
from collections import Counter

# Vocabulary with spaCy Russian tokenizer
class Vocabulary:
    nlp = spacy.load("ru_core_news_sm")

    def __init__(self, freq_threshold):
        self.itos = {0: "<PAD>", 1: "<SOS>", 2: "<EOS>", 3: "<UNK>"}
        self.stoi = {v: k for k, v in self.itos.items()}
        self.freq_threshold = freq_threshold

    def __len__(self): return len(self.itos)

    @staticmethod
    def tokenize(text):
        return [token.text.lower() for token in Vocabulary.nlp.tokenizer(text)]

    def build_vocab(self, sentence_list):
        frequencies = Counter()
        idx = len(self.itos)
        for sentence in sentence_list:
            for word in self.tokenize(sentence):
                frequencies[word] += 1
                if frequencies[word] == self.freq_threshold:
                    self.stoi[word] = idx
                    self.itos[idx] = word
                    idx += 1

    def numericalize(self, text):
        tokens = self.tokenize(text)
        return [self.stoi.get(tok, self.stoi["<UNK>"]) for tok in tokens]

# Dataset
class ProductDataset(Dataset):
    def __init__(self, root_dir, title_key="title", transform=None, freq_threshold=5):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.samples = []
        for sub in self.root_dir.iterdir():
            if not sub.is_dir(): continue
            img = sub / "image_1.webp"
            js = sub / "product_data.json"
            if img.exists() and js.exists():
                data = json.loads(js.read_text(encoding="utf-8"))
                title = data.get("product_data", {}).get(title_key, "").strip()
                if title: self.samples.append((img, title))
        if not self.samples:
            raise ValueError(f"No valid examples in {root_dir}")
        self.vocab = Vocabulary(freq_threshold)
        self.vocab.build_vocab([c for _, c in self.samples])

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        img_path, cap = self.samples[idx]
        img = Image.open(img_path).convert("RGB")
        if self.transform: img = self.transform(img)
        seq = [self.vocab.stoi["<SOS>"]] + self.vocab.numericalize(cap) + [self.vocab.stoi["<EOS>"]]
        return img, torch.tensor(seq, dtype=torch.long)

# Collate класс для padding
class PadCollate:
    def __init__(self, pad_idx): self.pad_idx = pad_idx
    def __call__(self, batch):
        imgs, caps = zip(*batch)
        imgs = torch.stack(imgs)
        caps = pad_sequence(caps, batch_first=True, padding_value=self.pad_idx)
        return imgs, caps

# DataLoader factory
def get_product_loader(root_dir, batch_size=32, shuffle=True, num_workers=4, freq_threshold=5):
    transform = T.Compose([
        T.Resize((224,224)), T.ToTensor(),
        T.Normalize((0.485,0.456,0.406),(0.229,0.224,0.225))
    ])
    ds = ProductDataset(root_dir, transform=transform, freq_threshold=freq_threshold)
    pad_idx = ds.vocab.stoi["<PAD>"]
    loader = DataLoader(ds, batch_size=batch_size, shuffle=shuffle,
                        num_workers=num_workers, collate_fn=PadCollate(pad_idx))
    return loader
def main():
    data_path = "C:/Users/Alexey Balakin/Desktop/ozon_data_test"

    transform = T.Compose([
        T.Resize(226),
        T.RandomCrop(224),
        T.ToTensor(),
        T.Normalize((0.485,0.456,0.406),(0.229,0.224,0.225))
    ])

    dataset = ProductDataset(data_path, transform=transform)
    loader = get_product_loader(data_path)

    print("Vocab size:", len(dataset.vocab))
    print("Dataset size:", len(dataset))
    print("First 5 items (caption indices lengths and raw captions):")
    for i in range(min(5, len(dataset))):
        img, cap_seq = dataset[i]
        print(f"[{i}] sequence length={cap_seq.size(0)}, indices={cap_seq.tolist()}")

    # Проверим батч из loader
    for images, captions in loader:
        print("Batch images shape:", images.shape)
        print("Batch captions shape:", captions.shape)
        break


if __name__ == '__main__':
    main()
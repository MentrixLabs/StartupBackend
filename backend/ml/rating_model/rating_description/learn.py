import os

os.environ["KERAS_BACKEND"] = "tensorflow"

import numpy as np
import keras
import tensorflow as tf
from keras import layers

from keras.layers import Embedding

from dataset import open_csv_files

df = open_csv_files('./data')

vectorizer = layers.TextVectorization(max_tokens=20000, output_sequence_length=200)
text_samples = df["text"].to_numpy()
text_ds = tf.data.Dataset.from_tensor_slices(text_samples).batch(128)
vectorizer.adapt(text_ds)

def create_dataset(dataframe, batch_size=32):
    text_vectorized = vectorizer(dataframe["text"].to_numpy())
    targets = dataframe["target"].to_numpy()
    
    dataset = tf.data.Dataset.from_tensor_slices(
        (text_vectorized, targets)
    )
    dataset = dataset.shuffle(buffer_size=len(dataframe))
    dataset = dataset.batch(batch_size)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset

train_ds = create_dataset(df, batch_size=32)

voc = vectorizer.get_vocabulary()
word_index = dict(zip(voc, range(len(voc))))

path_to_glove_file = "glove.6B.100d.txt"

embeddings_index = {}
with open(path_to_glove_file) as f:
    for line in f:
        word, coefs = line.split(maxsplit=1)
        coefs = np.fromstring(coefs, "f", sep=" ")
        embeddings_index[word] = coefs

print("Found %s word vectors." % len(embeddings_index))

num_tokens = len(voc) + 2
embedding_dim = 100
hits = 0
misses = 0

embedding_matrix = np.zeros((num_tokens, embedding_dim))
for word, i in word_index.items():
    embedding_vector = embeddings_index.get(word)
    if embedding_vector is not None:
        embedding_matrix[i] = embedding_vector
        hits += 1
    else:
        misses += 1
print("Converted %d words (%d misses)" % (hits, misses))

embedding_layer = Embedding(
    num_tokens,
    embedding_dim,
    trainable=False,
)
embedding_layer.build((1,))
embedding_layer.set_weights([embedding_matrix])

int_sequences_input = keras.Input(shape=(None,), dtype="int32")
embedded_sequences = embedding_layer(int_sequences_input)
x = layers.Conv1D(256, 5, activation="relu")(embedded_sequences)
x = layers.Conv1D(128, 5, activation="relu")(x)
x = layers.MaxPooling1D(5)(x)
x = layers.Conv1D(128, 5, activation="relu")(x)
x = layers.GlobalMaxPooling1D()(x)
x = layers.Dense(128, activation="relu")(x)
x = layers.Dropout(0.5)(x)
preds = layers.Dense(1)(x)
model = keras.Model(int_sequences_input, preds)
model.summary()

model.compile(
    optimizer="adam", loss="mse", metrics=["mae"]
)

model.fit(train_ds, epochs=20)

string_input = keras.Input(shape=(1,), dtype="string")
x = vectorizer(string_input)
preds = model(x)
end_to_end_model = keras.Model(string_input, preds)

probabilities = end_to_end_model(
    keras.ops.convert_to_tensor(
        [["Хорошая кружка, но хрупкая"]]
    )
)

print(probabilities)

end_to_end_model.save('model.keras')
end_to_end_model.export('model')

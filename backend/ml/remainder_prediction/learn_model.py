import pandas as pd
import numpy as np
import os

import tensorflow as tf

path_csv = 'output.csv'
df = pd.read_csv(path_csv, dtype={'category': str}, parse_dates=['dates'])
df['dates'] = pd.to_datetime(df['dates'])

df['day_of_year'] = df['dates'].dt.dayofyear
df['day_angle'] = 2 * np.pi * (df['day_of_year'] - 1) / 365.25
df['year_sin'] = np.sin(df['day_angle'])
df['year_cos'] = np.cos(df['day_angle'])

df['day_of_week'] = df['dates'].dt.dayofweek
df['day_angle'] = 2 * np.pi * df['day_of_week'] / 7
df['day_sin'] = np.sin(df['day_angle'])
df['day_cos'] = np.cos(df['day_angle'])

df = df.drop(['dates', 'day_of_year', 'day_angle', 'day_of_week'], axis=1)

counts_prices_norm = tf.keras.layers.Normalization()
counts_prices_norm.adapt(np.array(df[['counts', 'prices']]))

category_lookup   = tf.keras.layers.StringLookup(vocabulary=np.unique(df['category']))
category_encoding = tf.keras.layers.CategoryEncoding(
    num_tokens=category_lookup.vocabulary_size(),
    output_mode='one_hot'
)

ds = tf.data.Dataset.from_tensor_slices({
    'category': df['category'].values,
    'counts_prices': df[['counts', 'prices']].values,
    'date_feats': df[['year_sin', 'year_cos', 'day_sin', 'day_cos']].values
})

SEQ_LEN = 5

windows = ds.window(SEQ_LEN + 1, shift=1, drop_remainder=True)

windows = windows.flat_map(
    lambda win: tf.data.Dataset.zip({
        'category':    win['category'].batch(SEQ_LEN + 1),
        'counts_prices': win['counts_prices'].batch(SEQ_LEN + 1),
        'date_feats':  win['date_feats'].batch(SEQ_LEN + 1),
    })
)

def split_and_preprocess(batch):
    x_cat = batch['category'][:-1]
    x_num = batch['counts_prices'][:-1]
    x_date = batch['date_feats'][:-1]
    y_num = batch['counts_prices'][-1]

    y_num = tf.cast(y_num, tf.float32)

    return (
        {
            'category_seq': batch['category'][:-1],
            'counts_prices_seq': batch['counts_prices'][:-1],
            'date_seq': batch['date_feats'][:-1]
        },
        y_num
    )

dataset = windows.map(split_and_preprocess, num_parallel_calls=tf.data.AUTOTUNE)

BATCH_SIZE = 32

dataset = (dataset
            .cache()
            .shuffle(1000)
            .batch(BATCH_SIZE, drop_remainder=True)
            .prefetch(tf.data.AUTOTUNE)
            )

SEQ_LEN = None
cat_in  = tf.keras.Input(shape=(SEQ_LEN, 1), dtype=tf.string, name='category_seq')
num_in  = tf.keras.Input(shape=(SEQ_LEN, 2), dtype=tf.float32, name='counts_prices_seq')
date_in = tf.keras.Input(shape=(SEQ_LEN, 4), dtype=tf.float32, name='date_seq')

x_cat = category_lookup(cat_in)
x_cat = category_encoding(x_cat)

x_num = counts_prices_norm(num_in)

merged = tf.keras.layers.Concatenate()([x_cat, x_num, date_in])
x = tf.keras.layers.LSTM(128, return_sequences=True)(merged)
x = tf.keras.layers.LSTM(128)(x)
out = tf.keras.layers.Dense(2, name='num_output')(x)

model = tf.keras.Model([cat_in, num_in, date_in], out)

model.compile('adam', 'mse', metrics=['mae'])

model.summary()

history = model.fit(
    dataset,
    epochs=15,
    # validation_data=dataset.take(100)
)
model.save('model.keras')

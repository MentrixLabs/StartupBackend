import json
import os
import glob
import pandas as pd
import tensorflow as tf
import numpy as np

def open_csv_files(path_directory):
    filenames = glob.glob(path_directory + "/*.csv")

    dfs = []
    for filename in filenames:
        dfs.append(pd.read_csv(filename))

    big_frame = pd.concat(dfs, ignore_index=True)

    return big_frame

def dataset_create(path_directory, batch_size=32, shuffle_buffer=1000):
    df = open_csv_files(path_directory)

    print(df.head())
    print(df.dtypes)

    numeric_features = df['descriptions']
    target = df.pop('ratings')

    numeric_features = (numeric_features)

    numeric_dataset = tf.data.Dataset.from_tensor_slices((numeric_features, target))

    numeric_batches = numeric_dataset.shuffle(shuffle_buffer).batch(batch_size)

    return numeric_batches

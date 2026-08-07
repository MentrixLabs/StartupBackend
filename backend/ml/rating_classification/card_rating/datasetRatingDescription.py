import json
import os
import math
from .scaler import retingscaler
import tensorflow as tf
import numpy as np
import glob

def _serialize_example(description, rating):
        feature = {
            'description': tf.train.Feature(bytes_list=tf.train.BytesList(value=[description.numpy()])),
            'rating': tf.train.Feature(float_list=tf.train.FloatList(value=[rating.numpy()]))
        }
        example_proto = tf.train.Example(features=tf.train.Features(feature=feature))
        return example_proto.SerializeToString()

def _tf_serialize_example(description, rating):
        tf_string = tf.py_function(_serialize_example, [description, rating], tf.string)
        return tf.reshape(tf_string, ())

def ratingDescriptionDatasetSaveTFrecord(data_slices, tfrecord_path):
    dataset = tf.data.Dataset.from_tensor_slices(data_slices)
    serialized_dataset = dataset.map(_tf_serialize_example)
    writer = tf.data.experimental.TFRecordWriter(tfrecord_path)
    writer.write(serialized_dataset)

def jsonToListData(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    descriptions = []
    ratings = []

    for product in json_data['products']:
        product_data = product['product_data']

        if (product_data['description'] is not None and product_data['rating'] is not None and not math.isnan(product_data['rating'])):
            descriptions.append(' '.join(product_data['description']))
            ratings.append(product_data['rating'])
    
    return (descriptions, ratings)

def createDataset(json_directory, tfrecord_directory):
    json_paths = glob.glob(os.path.join(json_directory, '*.json'))
    tfrecord_paths = [
        os.path.join(tfrecord_directory, os.path.splitext(os.path.basename(json_path))[0] + '.tfrecord')
        for json_path in json_paths
    ]

    os.makedirs(tfrecord_directory, exist_ok=True)

    for json_path, tfrecord_path in zip(json_paths, tfrecord_paths):
        data_slices = jsonToListData(json_path)

        ratingDescriptionDatasetSaveTFrecord(data_slices, tfrecord_path)

def ratingDescriptionParseTFrecord(example_proto):
    feature_description = {
        'description': tf.io.FixedLenFeature([], tf.string),
        'rating': tf.io.FixedLenFeature([], tf.float32),
    }
    parsed = tf.io.parse_single_example(example_proto, feature_description)
    return parsed['description'], parsed['rating']

def loadDataset(tfrecord_directory, batch_size=32, shuffle_buffer=10_000):
    tfrecord_paths = glob.glob(os.path.join(tfrecord_directory, '*.tfrecord'))
    raw_dataset = tf.data.TFRecordDataset(tfrecord_paths)
    dataset = raw_dataset.map(ratingDescriptionParseTFrecord, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.shuffle(shuffle_buffer)
    dataset = dataset.batch(batch_size)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset

import tensorflow as tf


def load_and_preprocess_image(image_path, label=None, img_size=(224, 224)):
    image = tf.io.read_file(image_path)
    image = tf.image.decode_jpeg(image, channels=3)
    image = tf.image.resize(image, img_size)
    image = image / 255.0
    return (image, label) if label is not None else image


def create_dataset(data_files, batch_size=32, shuffle=True, is_train=True):
    if isinstance(data_files, (list, tuple)):
        image_paths, labels = data_files
        dataset = tf.data.Dataset.from_tensor_slices((image_paths, labels))
    else:
        dataset = data_files

    dataset = dataset.map(
        lambda x, y: load_and_preprocess_image(x, y),
        num_parallel_calls=tf.data.AUTOTUNE
    )

    if shuffle and is_train:
        dataset = dataset.shuffle(buffer_size=1000)

    return dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)

import tensorflow as tf

from card_rating.RatingDescription import RatingDescription
from card_rating.datasetRatingDescription import createDataset, loadDataset

if __name__ == '__main__':

    modelRatingDescription = RatingDescription()

    createDataset('dataset/description', 'dataset/data')

    dataset = loadDataset('dataset/data')

    modelRatingDescription.trainRatingDescription(dataset, epochs=5)

    while True:
        try:
            input_text = input('Описание товара: ')

            sentences = tf.constant([input_text])
            predictions = modelRatingDescription.model(sentences)

            print(predictions)
        except Exception as e:
            print(f'Error: {e}')

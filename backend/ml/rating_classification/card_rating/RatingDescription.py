import tensorflow as tf
import tensorflow_hub as hub
import tensorflow_text as text

class RatingDescriptionModel(tf.keras.Model):
    def __init__(self):
        super().__init__()
        self.tfhub_handle_encoder = 'https://kaggle.com/models/tensorflow/bert/TensorFlow2/multi-cased-l-12-h-768-a-12/3'
        self.tfhub_handle_preprocess = 'https://kaggle.com/models/tensorflow/bert/TensorFlow2/multi-cased-preprocess/3'

        self.preprocessing_layer = hub.KerasLayer(self.tfhub_handle_preprocess, name='description')
        self.encoder = hub.KerasLayer(self.tfhub_handle_encoder, trainable=False, name='BERT_encoder')
        self.dropout = tf.keras.layers.Dropout(0.6)
        self.dense = tf.keras.layers.Dense(64)
        self.classifier = tf.keras.layers.Dense(1, activation="relu", name='rating')

    def call(self, inputs):
        encoder_inputs = self.preprocessing_layer(inputs)
        outputs = self.encoder(encoder_inputs)
        pooled_output = outputs['pooled_output']
        x = self.dropout(pooled_output)
        x = self.dense(x)
        return self.classifier(x)


class RatingDescription:
    def __init__(self):
        self.model = RatingDescriptionModel()
        self.model.compile(
            optimizer="adam",
            loss="mse",
            metrics=["mae"],
            jit_compile=False
        )
        self.history = None

    def trainRatingDescription(self, dataset, validation_dataset=None, epochs=5):
        # callbacks = [
        #     tf.keras.callbacks.EarlyStopping(patience=2),
        #     tf.keras.callbacks.ModelCheckpoint('best_model.h5', save_best_only=True)
        # ]
        
        self.history = self.model.fit(
            dataset,
            validation_data=validation_dataset,
            epochs=epochs,
            # callbacks=callbacks
        )

        return self.history

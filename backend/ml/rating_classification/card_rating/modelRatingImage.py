import tensorflow as tf
import tensorflow_hub as hub


class RatingImage(tf.keras.Model):
    def __init__(self, input_shape=(224, 224, 3), embedding_dim=256):
        super().__init__()

        self.input_shape = input_shape

        self.base_model = tf.keras.applications.EfficientNetB0(weights='imagenet', include_top=False, input_shape=self.input_shape)
        self.base_model.trainable = False

        self.gap = tf.keras.layers.GlobalAveragePooling2D()
        self.embedding_layer = tf.keras.layers.Dense(embedding_dim, activation='relu')
        self.classifier = tf.keras.layers.Dense(1, activation='sigmoid')

    def call(self, inputs, training=False):
        x = self.base_model(inputs, training=training)
        x = self.gap(x)
        embeddings = self.embedding_layer(x)
        predictions = self.classifier(embeddings)
        return predictions

    def build_graph(self):
        x = tf.keras.Input(shape=self.input_shape)
        return tf.keras.Model(inputs=[x], outputs=self.call(x))


if __name__ == '__main__':
    model = RatingImage()

    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    model.build_graph().summary()

import tensorflow as tf

model = tf.keras.models.load_model("model.keras")

def rating_description_prediction(description: str):
    try:
        predictions = model(tf.constant([[description]]))
        return predictions.numpy()[0][0]
    except Exception as e:
        print(f"Error model_rating_description: {str(e)}")
        return None

if __name__ == "__main__":
    predictions = rating_description_prediction("Хорошая кружка, но хрупкая")
    print(predictions)

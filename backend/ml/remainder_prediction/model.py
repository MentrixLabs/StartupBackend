import numpy as np
import tensorflow as tf
import tensorflow.keras.config as tfconfig
import keras
from datetime import timedelta

import logging

logger = logging.getLogger(__name__)

tfconfig.enable_unsafe_deserialization()
model = keras.models.load_model('ml/remainder_prediction/assets/model.keras')

def prediction_days(data, days):
    logger.info("2.1")
    data = data.copy()
    data['dates'] = pd.to_datetime(data['dates'])

    logger.info("2")

    cat = data[['category']].values.astype('str')
    num = data[['counts', 'prices']].values.astype('float32')
    dates = data['dates']

    results = []

    logger.info("3")

    for _ in range(days):
        last_date = pd.DataFrame()
        
        logger.info("4")

        next_date = dates.values[-1] + pd.DateOffset(days=1)
        last_date['day_of_year'] = dates.dt.dayofyear
        last_date['day_angle'] = 2 * np.pi * (last_date['day_of_year'] - 1) / 365.25
        last_date['year_sin'] = np.sin(last_date['day_angle'])
        last_date['year_cos'] = np.cos(last_date['day_angle'])

        last_date['day_of_week'] = dates.dt.dayofweek
        last_date['day_angle'] = 2 * np.pi * last_date['day_of_week'] / 7
        last_date['day_sin'] = np.sin(last_date['day_angle'])
        last_date['day_cos'] = np.cos(last_date['day_angle'])

        date_features = last_date[['year_sin', 'year_cos', 'day_sin', 'day_cos']].values.astype('float32')

        y_pred = model({
            'category_seq': tf.convert_to_tensor(cat[None, ...]),
            'counts_prices_seq': tf.convert_to_tensor(num[None, ...]),
            'date_seq': tf.convert_to_tensor(date_features[None, ...])
        }).numpy()

        logger.info("5")

        cat = np.concatenate([cat, [cat[-1]]])
        num = np.concatenate([num, y_pred])
        dates = pd.concat([dates, pd.Series([next_date])])

        results.append({
            'category': cat[-1][0],
            'dates': next_date,
            'counts': y_pred[0][0],
            'prices': y_pred[0][1]
        })
        logger.info("6")

    predictions_df = pd.DataFrame(results)
    return predictions_df

def prediction_days_json(data, days=40):
    logger.info("1.1")
    df = pd.DataFrame({
        'category': data.get('category', 'other'),
        'dates': pd.to_datetime(data['dates']).strftime('%Y-%m-%d'),
        'counts': data['counts'],
        'prices': data['prices']
    })

    logger.info("1")

    predictions = prediction_days(df, days)

    output_json = {
        # 'product_id': data.get('product_id', None),
        'category': predictions['category'][0],
        'dates': predictions['dates'].dt.strftime('%Y-%m-%d').tolist(),
        'counts': predictions['counts'].astype(float).tolist(),
        'prices': predictions['prices'].astype(float).tolist(),
    }

    logger.info("-1")

    return output_json

if __name__ == '__main__':
    json = {"product_id": 1001402, "category": "construction.tools.light", "dates": ["2020-04-16 19:48:14 UTC"], "prices": [75.68], "counts": [1]}
    predictions = prediction_days_json(json, day=30)
    print(predictions)

    from io import StringIO
    
    data = """
    other,2019-11-12,2.031961917715063,121.44764705882353
    other,2019-11-13,1.9886605244507443,128.02552799433025
    other,2019-11-14,2.0188383045525904,137.92305337519625
    other,2019-11-15,0.0,64.33
    other,2019-11-16,2.4309365362765787,167.89686414543092
    other,2019-11-17,3.564185110663984,156.44593400402414
    other,2019-11-18,2.0926629640456005,120.14062262496347
    """

    df = pd.read_csv(
        StringIO(data),
        names=['category','dates','counts','prices']
    )

    predictions = prediction_days(df, 30)

    print(predictions)

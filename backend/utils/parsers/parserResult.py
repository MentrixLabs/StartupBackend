class ParsingData:

    @classmethod
    def result(cls, url, timestamp):
        return {
            "url": url,
            "timestamp": timestamp.isoformat(),
            "success": False,
            "product_data": ParsingData.product_data()
        }

    @classmethod
    def product_data(cls):
        return {
            "product_id": None,     # str
            "provider": None,       # str
            "category": None,       # str
            "brand": None,          # str
            "title": None,          # str
            "description": None,    # str
            "original_price": None, # int
            "price": None,          # int
            "currency": None,       # str
            "rating": None,         # float
            "reviews_count": None,  # int
            "reviews": None         # {uuid: str}
        }

    @classmethod
    def product_review(cls):
        return {
            "review_date": None,     # str
            "reviewer_name": None,   # str
            "review_text": None,     # str
            "review_comments": None, # [str]
            "positive_help": None,   # int
            "negative_help": None,   # int
            "review_rating": None,   # int
            "review_images": None    # {uuid: str}
        }
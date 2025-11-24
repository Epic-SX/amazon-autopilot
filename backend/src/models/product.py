class ProductDetail:
    def __init__(self, 
                 source=None,
                 title=None, 
                 price=None, 
                 url=None, 
                 image_url=None, 
                 description=None, 
                 availability=True,
                 shop=None,
                 rating=None,
                 review_count=None,
                 shipping_fee=None,
                 delivery_date=None,
                 additional_info=None,
                 ranking=None,
                 asin=None):
        self.source = source  # 情報元（Amazon, 楽天, Yahoo, 価格.com）
        self.title = title  # 商品タイトル
        self.price = price  # 価格
        self.url = url  # 商品URL
        self.image_url = image_url  # 商品画像URL
        self.description = description  # 商品説明
        self.availability = availability  # 在庫状況
        self.shop = shop  # 販売店舗名
        self.rating = rating  # 評価（星の数など）
        self.review_count = review_count  # レビュー数
        self.shipping_fee = shipping_fee  # 送料
        self.delivery_date = delivery_date  # 配送予定日
        self.additional_info = additional_info or {}  # その他の情報
        self.ranking = ranking  # ランキング（検索結果での順位や人気度）
        self.asin = asin  # Amazon Standard Identification Number
        
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'source': self.source,
            'title': self.title,
            'price': self.price,
            'url': self.url,
            'image_url': self.image_url,
            'description': self.description,
            'availability': self.availability,
            'shop': self.shop,
            'rating': self.rating,
            'review_count': self.review_count,
            'shipping_fee': self.shipping_fee,
            'delivery_date': self.delivery_date,
            'additional_info': self.additional_info,
            'ranking': self.ranking,
            'asin': self.asin
        } 
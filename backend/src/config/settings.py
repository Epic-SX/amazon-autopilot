import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys and Configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY", "")

# EC Site API Keys
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID", "")
RAKUTEN_APP_SECRET = os.getenv("RAKUTEN_APP_SECRET", "")
RAKUTEN_AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID", "")

YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID", "")

KAKAKU_SHOP_CD = os.getenv("KAKAKU_SHOP_CD", "")
KAKAKU_API_KEY = os.getenv("KAKAKU_API_KEY", "")
KAKAKU_OAUTH_SECRET = os.getenv("KAKAKU_OAUTH_SECRET", "")

AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "")
AMAZON_ACCESS_KEY = os.getenv("AMAZON_ACCESS_KEY", "")
AMAZON_SECRET_KEY = os.getenv("AMAZON_SECRET_KEY", "")
AMAZON_REGION = os.getenv("AMAZON_REGION", "ap-northeast-1")

# API Endpoints
AMAZON_API_ENDPOINT = "https://webservices.amazon.co.jp"
RAKUTEN_API_ENDPOINT = "https://app.rakuten.co.jp/services/api"
YAHOO_API_ENDPOINT = "https://shopping.yahooapis.jp/ShoppingWebService/V3"
KAKAKU_API_ENDPOINT = "https://kakakucom.api.webservice.jp"
GOOGLE_VISION_API_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"

# Search Configuration
MAX_SEARCH_RESULTS = 5
MIN_SIMILARITY_SCORE = 0.8
PRICE_THRESHOLD = 0.9  # 90% similarity for price comparison 
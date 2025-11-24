def clean_text(text):
    """
    テキストのクリーニング
    - 余分な空白の削除
    - 特殊文字の処理
    """
    if not text:
        return ""
    
    # 基本的なテキストクリーニング
    cleaned = text.strip()
    # 複数の空白を1つに
    cleaned = " ".join(cleaned.split())
    return cleaned

def validate_product_info(product_info):
    """
    商品情報の検証
    """
    if not product_info:
        return False
        
    # 空白文字のみの場合はFalse
    if not product_info.strip():
        return False
        
    # 最小文字数チェック（例：2文字以上）
    if len(product_info.strip()) < 2:
        return False
        
    return True 
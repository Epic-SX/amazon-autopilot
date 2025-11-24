import requests
import base64
import json
import io
from ..config.settings import GOOGLE_CLOUD_API_KEY, GOOGLE_VISION_API_ENDPOINT

class ImageSearchEngine:
    def __init__(self):
        self.api_key = GOOGLE_CLOUD_API_KEY
        self.endpoint = GOOGLE_VISION_API_ENDPOINT

    def search_similar_images(self, image_data=None, image_url=None):
        """
        画像データまたはURLから類似画像を検索
        """
        try:
            if not image_data and not image_url:
                raise ValueError("Either image_data or image_url must be provided")
                
            # Google Cloud Vision APIリクエストの準備
            request_data = {
                "requests": [
                    {
                        "features": [
                            {
                                "type": "WEB_DETECTION",
                                "maxResults": 10
                            }
                        ]
                    }
                ]
            }
            
            # 画像データまたはURLを設定
            if image_data:
                # Base64エンコードされた画像データを使用
                request_data["requests"][0]["image"] = {
                    "content": base64.b64encode(image_data).decode('utf-8')
                }
            else:
                # 画像URLを使用
                request_data["requests"][0]["image"] = {
                    "source": {
                        "imageUri": image_url
                    }
                }
            
            # APIリクエストを送信
            api_url = f"{self.endpoint}?key={self.api_key}"
            response = requests.post(api_url, json=request_data)
            
            if response.status_code != 200:
                print(f"Error in Google Vision API: {response.status_code} - {response.text}")
                return self._get_fallback_results()
                
            result = response.json()
            
            # レスポンスから類似商品情報を抽出
            if 'responses' in result and len(result['responses']) > 0:
                web_detection = result['responses'][0].get('webDetection', {})
                return self.process_similar_products(web_detection)
            
            return self._get_fallback_results()
            
        except Exception as e:
            print(f"Error in image search: {e}")
            return self._get_fallback_results()

    def extract_model_numbers(self, image_data=None, image_url=None):
        """
        画像からモデル番号を抽出
        """
        try:
            if not image_data and not image_url:
                raise ValueError("Either image_data or image_url must be provided")
                
            # Google Cloud Vision APIリクエストの準備
            request_data = {
                "requests": [
                    {
                        "features": [
                            {
                                "type": "TEXT_DETECTION",
                                "maxResults": 10
                            }
                        ]
                    }
                ]
            }
            
            # 画像データまたはURLを設定
            if image_data:
                # Base64エンコードされた画像データを使用
                request_data["requests"][0]["image"] = {
                    "content": base64.b64encode(image_data).decode('utf-8')
                }
            else:
                # 画像URLを使用
                request_data["requests"][0]["image"] = {
                    "source": {
                        "imageUri": image_url
                    }
                }
            
            # APIリクエストを送信
            api_url = f"{self.endpoint}?key={self.api_key}"
            print(f"Sending request to Google Vision API for text detection: {api_url}")
            
            try:
                response = requests.post(api_url, json=request_data)
                
                if response.status_code != 200:
                    print(f"Error in Google Vision API: {response.status_code} - {response.text}")
                    return []
                    
                result = response.json()
                
                # レスポンスからテキストを抽出
                if 'responses' in result and len(result['responses']) > 0:
                    text_annotations = result['responses'][0].get('textAnnotations', [])
                    return self._extract_model_numbers_from_text(text_annotations)
                
                return []
            except Exception as e:
                print(f"Exception during Google Vision API request: {e}")
                # Return empty list instead of failing
                return []
                
        except Exception as e:
            print(f"Error in extract_model_numbers: {e}")
            return []
    
    def _extract_model_numbers_from_text(self, text_annotations):
        """
        テキスト注釈からモデル番号を抽出
        """
        import re
        
        model_numbers = []
        
        # モデル番号のパターン (例: ABC-123, XYZ123など)
        model_patterns = [
            r'[A-Z0-9]{2,}-[A-Z0-9]{2,}',  # ABC-123 形式
            r'[A-Z]{2,}[0-9]{2,}',          # ABC123 形式
            r'[0-9]{2,}-[A-Z0-9]{2,}'       # 12-ABC 形式
        ]
        
        if text_annotations:
            # 最初の要素は全テキスト、残りは個別のテキスト領域
            full_text = text_annotations[0].get('description', '')
            
            # 各パターンでモデル番号を検索
            for pattern in model_patterns:
                matches = re.findall(pattern, full_text)
                for match in matches:
                    # 信頼度は固定値 (実際のAPIでは異なる可能性あり)
                    model_numbers.append({
                        'model_number': match,
                        'confidence': 0.9,
                        'source': 'text_detection'
                    })
            
            # 重複を削除
            unique_models = []
            seen = set()
            for model in model_numbers:
                if model['model_number'] not in seen:
                    seen.add(model['model_number'])
                    unique_models.append(model)
            
            # 信頼度でソート
            unique_models.sort(key=lambda x: x['confidence'], reverse=True)
            
            return unique_models
        
        return []
    
    def analyze_image_content(self, image_data=None, image_url=None):
        """
        画像の内容を分析して、何が写っているかを識別
        """
        try:
            if not image_data and not image_url:
                raise ValueError("Either image_data or image_url must be provided")
                
            # Google Cloud Vision APIリクエストの準備 - 検出機能を増やす
            request_data = {
                "requests": [
                    {
                        "features": [
                            {
                                "type": "LABEL_DETECTION",
                                "maxResults": 20
                            },
                            {
                                "type": "OBJECT_LOCALIZATION",
                                "maxResults": 10
                            },
                            {
                                "type": "LOGO_DETECTION",
                                "maxResults": 5
                            },
                            {
                                "type": "IMAGE_PROPERTIES",
                                "maxResults": 5
                            },
                            {
                                "type": "WEB_DETECTION",
                                "maxResults": 5
                            }
                        ]
                    }
                ]
            }
            
            # 画像データまたはURLを設定
            if image_data:
                # Base64エンコードされた画像データを使用
                request_data["requests"][0]["image"] = {
                    "content": base64.b64encode(image_data).decode('utf-8')
                }
            else:
                # 画像URLを使用
                request_data["requests"][0]["image"] = {
                    "source": {
                        "imageUri": image_url
                    }
                }
            
            # APIリクエストを送信
            api_url = f"{self.endpoint}?key={self.api_key}"
            print(f"Sending request to Google Vision API for image analysis: {api_url}")
            
            try:
                response = requests.post(api_url, json=request_data)
                
                if response.status_code != 200:
                    print(f"Error in Google Vision API: {response.status_code} - {response.text}")
                    # Return a fallback term instead of failing
                    return self._get_fallback_generic_term()
                    
                result = response.json()
                
                # レスポンスからより詳細な情報を抽出
                if 'responses' in result and len(result['responses']) > 0:
                    response = result['responses'][0]
                    
                    # ラベル検出結果
                    labels = response.get('labelAnnotations', [])
                    
                    # オブジェクト検出結果
                    objects = response.get('localizedObjectAnnotations', [])
                    
                    # ロゴ検出結果
                    logos = response.get('logoAnnotations', [])
                    
                    # Web検出結果
                    web_detection = response.get('webDetection', {})
                    web_entities = web_detection.get('webEntities', [])
                    
                    # 詳細な情報を元に検索キーワードを生成
                    return self._generate_detailed_search_term(labels, objects, logos, web_entities)
                
                return self._get_fallback_generic_term()
            except Exception as e:
                print(f"Exception during Google Vision API request: {e}")
                # Return a fallback term instead of failing
                return self._get_fallback_generic_term()
                
        except Exception as e:
            print(f"Error in analyze_image_content: {e}")
            return self._get_fallback_generic_term()
    
    def _generate_japanese_search_term(self, labels, objects):
        """
        検出されたラベルとオブジェクトから日本語の検索キーワードを生成
        """
        # 英語から日本語への簡易変換辞書
        en_to_jp = {
            'rope': 'ロープ',
            'cord': 'コード',
            'cable': 'ケーブル',
            'wire': 'ワイヤー',
            'string': '紐',
            'twine': '麻紐',
            'line': 'ライン',
            'thread': '糸',
            'yarn': '毛糸',
            'fiber': '繊維',
            'textile': '織物',
            'fabric': '布地',
            'cloth': '布',
            'material': '素材',
            'product': '製品',
            'item': '商品',
            'goods': '商品',
            'merchandise': '商品',
            'accessory': 'アクセサリー',
            'tool': '工具',
            'equipment': '機器',
            'device': 'デバイス',
            'machine': '機械',
            'appliance': '家電',
            'furniture': '家具',
            'clothing': '衣類',
            'apparel': 'アパレル',
            'footwear': '履物',
            'shoe': '靴',
            'bag': 'バッグ',
            'purse': '財布',
            'wallet': '財布',
            'watch': '腕時計',
            'jewelry': 'ジュエリー',
            'accessory': 'アクセサリー',
            'electronic': '電子機器',
            'computer': 'コンピューター',
            'phone': '電話',
            'smartphone': 'スマートフォン',
            'tablet': 'タブレット',
            'camera': 'カメラ',
            'television': 'テレビ',
            'audio': 'オーディオ',
            'speaker': 'スピーカー',
            'headphone': 'ヘッドフォン',
            'earphone': 'イヤフォン',
            'charger': '充電器',
            'adapter': 'アダプター',
            'battery': 'バッテリー',
            'power': '電源',
            'light': '照明',
            'lamp': 'ランプ',
            'bulb': '電球',
            'furniture': '家具',
            'chair': '椅子',
            'table': 'テーブル',
            'desk': '机',
            'bed': 'ベッド',
            'sofa': 'ソファ',
            'shelf': '棚',
            'cabinet': '収納',
            'drawer': '引き出し',
            'kitchen': 'キッチン',
            'bathroom': '浴室',
            'living': 'リビング',
            'bedroom': '寝室',
            'office': 'オフィス',
            'outdoor': '屋外',
            'garden': '庭',
            'tool': '工具',
            'hardware': '金物',
            'fastener': '留め具',
            'screw': 'ネジ',
            'nail': '釘',
            'bolt': 'ボルト',
            'nut': 'ナット',
            'washer': 'ワッシャー',
            'hook': 'フック',
            'chain': 'チェーン',
            'lock': '錠',
            'key': '鍵',
            'handle': 'ハンドル',
            'knob': 'ノブ',
            'switch': 'スイッチ',
            'button': 'ボタン',
            'remote': 'リモコン',
            'controller': 'コントローラー',
            'game': 'ゲーム',
            'toy': 'おもちゃ',
            'book': '本',
            'magazine': '雑誌',
            'newspaper': '新聞',
            'stationery': '文房具',
            'pen': 'ペン',
            'pencil': '鉛筆',
            'marker': 'マーカー',
            'paper': '紙',
            'notebook': 'ノート',
            'calendar': 'カレンダー',
            'card': 'カード',
            'envelope': '封筒',
            'box': '箱',
            'container': '容器',
            'bottle': 'ボトル',
            'can': '缶',
            'jar': '瓶',
            'cup': 'カップ',
            'mug': 'マグ',
            'glass': 'グラス',
            'plate': '皿',
            'bowl': 'ボウル',
            'utensil': '食器',
            'cutlery': 'カトラリー',
            'fork': 'フォーク',
            'knife': 'ナイフ',
            'spoon': 'スプーン',
            'chopsticks': '箸',
            'food': '食品',
            'drink': '飲料',
            'beverage': '飲み物',
            'snack': 'スナック',
            'candy': 'キャンディ',
            'chocolate': 'チョコレート',
            'cookie': 'クッキー',
            'cake': 'ケーキ',
            'bread': 'パン',
            'fruit': '果物',
            'vegetable': '野菜',
            'meat': '肉',
            'fish': '魚',
            'seafood': '海鮮',
            'dairy': '乳製品',
            'cheese': 'チーズ',
            'milk': '牛乳',
            'yogurt': 'ヨーグルト',
            'ice cream': 'アイスクリーム',
            'dessert': 'デザート',
            'meal': '食事',
            'breakfast': '朝食',
            'lunch': '昼食',
            'dinner': '夕食',
            'snack': '間食',
            'pet': 'ペット',
            'dog': '犬',
            'cat': '猫',
            'bird': '鳥',
            'fish': '魚',
            'plant': '植物',
            'flower': '花',
            'tree': '木',
            'grass': '草',
            'vehicle': '乗り物',
            'car': '車',
            'bicycle': '自転車',
            'motorcycle': 'バイク',
            'truck': 'トラック',
            'bus': 'バス',
            'train': '電車',
            'airplane': '飛行機',
            'boat': 'ボート',
            'ship': '船',
            'helmet': 'ヘルメット',
            'glove': '手袋',
            'hat': '帽子',
            'cap': 'キャップ',
            'scarf': 'スカーフ',
            'tie': 'ネクタイ',
            'belt': 'ベルト',
            'sock': '靴下',
            'shoe': '靴',
            'boot': 'ブーツ',
            'sandal': 'サンダル',
            'slipper': 'スリッパ',
            'jacket': 'ジャケット',
            'coat': 'コート',
            'sweater': 'セーター',
            'shirt': 'シャツ',
            't-shirt': 'Tシャツ',
            'pants': 'パンツ',
            'jeans': 'ジーンズ',
            'shorts': 'ショートパンツ',
            'skirt': 'スカート',
            'dress': 'ドレス',
            'suit': 'スーツ',
            'uniform': '制服',
            'underwear': '下着',
            'swimwear': '水着',
            'sleepwear': 'パジャマ',
            'baby': '赤ちゃん',
            'child': '子供',
            'adult': '大人',
            'man': '男性',
            'woman': '女性',
            'boy': '男の子',
            'girl': '女の子',
            'senior': '高齢者',
            'family': '家族',
            'friend': '友人',
            'colleague': '同僚',
            'neighbor': '隣人',
            'stranger': '見知らぬ人',
            'customer': '顧客',
            'client': 'クライアント',
            'patient': '患者',
            'doctor': '医師',
            'nurse': '看護師',
            'teacher': '教師',
            'student': '学生',
            'worker': '労働者',
            'employee': '従業員',
            'manager': '管理者',
            'boss': '上司',
            'owner': '所有者',
            'seller': '販売者',
            'buyer': '購入者',
            'artist': 'アーティスト',
            'musician': '音楽家',
            'actor': '俳優',
            'actress': '女優',
            'singer': '歌手',
            'dancer': 'ダンサー',
            'writer': '作家',
            'author': '著者',
            'photographer': '写真家',
            'designer': 'デザイナー',
            'engineer': 'エンジニア',
            'scientist': '科学者',
            'researcher': '研究者',
            'programmer': 'プログラマー',
            'developer': '開発者',
            'analyst': 'アナリスト',
            'consultant': 'コンサルタント',
            'advisor': 'アドバイザー',
            'coach': 'コーチ',
            'trainer': 'トレーナー',
            'instructor': 'インストラクター',
            'guide': 'ガイド',
            'host': 'ホスト',
            'hostess': 'ホステス',
            'waiter': 'ウェイター',
            'waitress': 'ウェイトレス',
            'chef': 'シェフ',
            'cook': '料理人',
            'baker': 'パン職人',
            'butcher': '肉屋',
            'fishmonger': '魚屋',
            'grocer': '八百屋',
            'pharmacist': '薬剤師',
            'cashier': 'レジ係',
            'clerk': '事務員',
            'secretary': '秘書',
            'receptionist': '受付',
            'security guard': '警備員',
            'police officer': '警察官',
            'firefighter': '消防士',
            'soldier': '兵士',
            'pilot': 'パイロット',
            'driver': 'ドライバー',
            'captain': '船長',
            'sailor': '船員',
            'astronaut': '宇宙飛行士',
            'explorer': '探検家',
            'adventurer': '冒険家',
            'traveler': '旅行者',
            'tourist': '観光客',
            'visitor': '訪問者',
            'guest': 'ゲスト',
            'resident': '住民',
            'citizen': '市民',
            'foreigner': '外国人',
            'immigrant': '移民',
            'refugee': '難民',
            'prisoner': '囚人',
            'suspect': '容疑者',
            'criminal': '犯罪者',
            'victim': '被害者',
            'witness': '目撃者',
            'plaintiff': '原告',
            'defendant': '被告',
            'lawyer': '弁護士',
            'judge': '裁判官',
            'jury': '陪審員',
            'politician': '政治家',
            'president': '大統領',
            'prime minister': '首相',
            'king': '王',
            'queen': '女王',
            'prince': '王子',
            'princess': '王女',
            'emperor': '皇帝',
            'empress': '皇后',
            'leader': 'リーダー',
            'follower': 'フォロワー',
            'supporter': '支持者',
            'opponent': '反対者',
            'ally': '同盟者',
            'enemy': '敵',
            'friend': '友人',
            'foe': '敵',
            'partner': 'パートナー',
            'spouse': '配偶者',
            'husband': '夫',
            'wife': '妻',
            'fiancé': '婚約者',
            'fiancée': '婚約者',
            'boyfriend': '彼氏',
            'girlfriend': '彼女',
            'lover': '恋人',
            'ex': '元恋人',
            'parent': '親',
            'father': '父',
            'mother': '母',
            'child': '子',
            'son': '息子',
            'daughter': '娘',
            'baby': '赤ちゃん',
            'infant': '幼児',
            'toddler': '幼児',
            'kid': '子供',
            'teenager': '十代',
            'youth': '若者',
            'adult': '大人',
            'middle-aged': '中年',
            'elderly': '高齢者',
            'senior': 'シニア',
            'retiree': '退職者',
            'ancestor': '先祖',
            'descendant': '子孫',
            'grandparent': '祖父母',
            'grandfather': '祖父',
            'grandmother': '祖母',
            'grandchild': '孫',
            'grandson': '孫息子',
            'granddaughter': '孫娘',
            'sibling': '兄弟姉妹',
            'brother': '兄弟',
            'sister': '姉妹',
            'twin': '双子',
            'triplet': '三つ子',
            'quadruplet': '四つ子',
            'quintuplet': '五つ子',
            'relative': '親戚',
            'kin': '親族',
            'family': '家族',
            'uncle': '叔父',
            'aunt': '叔母',
            'nephew': '甥',
            'niece': '姪',
            'cousin': 'いとこ',
            'in-law': '義理の家族',
            'father-in-law': '義父',
            'mother-in-law': '義母',
            'son-in-law': '義理の息子',
            'daughter-in-law': '義理の娘',
            'brother-in-law': '義理の兄弟',
            'sister-in-law': '義理の姉妹',
            'stepparent': '継親',
            'stepfather': '継父',
            'stepmother': '継母',
            'stepchild': '継子',
            'stepson': '継息子',
            'stepdaughter': '継娘',
            'stepbrother': '継兄弟',
            'stepsister': '継姉妹',
            'half-brother': '異父兄弟',
            'half-sister': '異父姉妹',
            'foster parent': '里親',
            'foster child': '里子',
            'adoptive parent': '養親',
            'adoptive child': '養子',
            'godparent': '名付け親',
            'godchild': '名付け子',
            'godfather': '名付け親',
            'godmother': '名付け親',
            'godson': '名付け子',
            'goddaughter': '名付け子'
        }
        
        # 検出されたラベルとオブジェクトを収集
        detected_items = []
        
        # ラベルから収集
        for label in labels:
            description = label.get('description', '').lower()
            score = label.get('score', 0)
            
            if score > 0.7:  # 信頼度が高いもののみ
                detected_items.append({
                    'description': description,
                    'score': score
                })
        
        # オブジェクトから収集
        for obj in objects:
            name = obj.get('name', '').lower()
            score = obj.get('score', 0)
            
            if score > 0.7:  # 信頼度が高いもののみ
                detected_items.append({
                    'description': name,
                    'score': score
                })
        
        # 信頼度でソート
        detected_items.sort(key=lambda x: x['score'], reverse=True)
        
        # 最も信頼度の高いアイテムを選択
        if detected_items:
            top_item = detected_items[0]['description']
            
            # 英語から日本語に変換
            if top_item in en_to_jp:
                return en_to_jp[top_item]
            
            # 変換辞書にない場合は、ロープのような画像の場合のデフォルト値
            if 'rope' in [item['description'] for item in detected_items]:
                return 'ロープ'
            if 'cord' in [item['description'] for item in detected_items]:
                return 'コード'
            if 'cable' in [item['description'] for item in detected_items]:
                return 'ケーブル'
            if 'wire' in [item['description'] for item in detected_items]:
                return 'ワイヤー'
            
            # それでもない場合は「商品」を返す
            return '商品'
        
        return self._get_fallback_generic_term()
    
    def _get_fallback_generic_term(self):
        """
        画像分析が失敗した場合のフォールバック検索語
        """
        # 一般的な商品カテゴリーのリスト
        common_categories = [
            "スマートフォン",  # Smartphone
            "テレビ",         # TV
            "カメラ",         # Camera
            "パソコン",       # Computer
            "家電",           # Home appliance
            "時計",           # Watch
            "バッグ",         # Bag
            "靴",             # Shoes
            "衣類",           # Clothing
            "アクセサリー"    # Accessory
        ]
        
        # ランダムに一つ選択
        import random
        return random.choice(common_categories)

    def process_similar_products(self, web_detection):
        """
        Web Detection結果から類似商品情報を抽出
        """
        similar_products = []
        
        # 視覚的に類似した画像の処理
        visual_matches = web_detection.get('visuallySimilarImages', [])
        for match in visual_matches[:10]:  # 上位10件を取得 (増やして後でフィルタリングできるようにする)
            product = {
                'image_url': match.get('url'),
                'score': round(float(match.get('score', 0.0)), 2) if 'score' in match else 0.0,
                'title': self._extract_title(match),
                'price': 0,  # デフォルト価格
                'source': 'unknown',  # デフォルトソース
                'store': 'unknown',  # デフォルトストア
                'product_url': match.get('url'),  # 商品URLをデフォルトで画像URLに設定
                'ranking': 0  # ランキング情報を追加
            }
            similar_products.append(product)
            
        # 完全一致または部分一致の画像も追加
        full_matches = web_detection.get('fullMatchingImages', [])
        for match in full_matches[:5]:  # 上位5件を取得
            product = {
                'image_url': match.get('url'),
                'score': 1.0,  # 完全一致は最高スコア
                'title': self._extract_title(match),
                'match_type': 'exact',
                'price': 0,  # デフォルト価格
                'source': 'unknown',  # デフォルトソース
                'store': 'unknown',  # デフォルトストア
                'product_url': match.get('url'),  # 商品URLをデフォルトで画像URLに設定
                'ranking': 0  # ランキング情報を追加
            }
            similar_products.append(product)

        # スコアに基づいてランキングを設定
        similar_products.sort(key=lambda x: x['score'], reverse=True)
        for i, product in enumerate(similar_products):
            product['ranking'] = i + 1

        return similar_products

    def _extract_title(self, match):
        """
        画像から商品タイトルを抽出（可能な場合）
        """
        # ページタイトルやラベルから商品名を推測
        if 'pageTitle' in match:
            return match['pageTitle']
        return "類似商品"
        
    def _get_fallback_results(self):
        """
        APIエラー時のフォールバック結果を返す
        """
        return [
            {
                'image_url': "https://placehold.co/300x300/eee/999?text=Similar+Product+1",
                'score': 0.95,
                'title': "類似商品 1"
            },
            {
                'image_url': "https://placehold.co/300x300/eee/999?text=Similar+Product+2",
                'score': 0.87,
                'title': "類似商品 2"
            },
            {
                'image_url': "https://placehold.co/300x300/eee/999?text=Similar+Product+3",
                'score': 0.82,
                'title': "類似商品 3"
            }
        ] 

    def _generate_detailed_search_term(self, labels, objects, logos, web_entities):
        """
        より詳細な情報を元に検索キーワードを生成
        """
        try:
            # Brand/Logo detection - highest priority
            brand = None
            for logo in logos:
                if logo.get('description') and logo.get('score', 0) > 0.7:
                    brand = logo.get('description')
                    break
            
            # Object detection - second priority
            object_types = []
            primary_object = None
            for obj in objects:
                if obj.get('score', 0) > 0.7:
                    object_types.append(obj.get('name', '').lower())
                    if not primary_object and ('laptop' in obj.get('name', '').lower() or 
                                              'computer' in obj.get('name', '').lower() or
                                              'notebook' in obj.get('name', '').lower() or
                                              'screen' in obj.get('name', '').lower() or
                                              'monitor' in obj.get('name', '').lower()):
                        primary_object = obj.get('name')
            
            # Label detection - third priority
            label_types = []
            for label in labels:
                if label.get('score', 0) > 0.7:
                    label_types.append(label.get('description', '').lower())
            
            # Web entities - additional information
            web_descriptions = []
            for entity in web_entities:
                if entity.get('score', 0) > 0.5:
                    web_descriptions.append(entity.get('description', '').lower())
            
            # Construct final product term
            product_terms = []
            
            # Start with brand if available
            if brand:
                product_terms.append(brand)
            
            # Add primary object type
            if primary_object:
                product_terms.append(primary_object)
            # If no primary object found but we have computer-related labels
            elif any(term in label_types for term in ['laptop', 'computer', 'notebook', 'pc']):
                for term in ['laptop', 'computer', 'notebook', 'pc']:
                    if term in label_types:
                        product_terms.append(term)
                        break
            
            # Add other relevant information from objects and labels
            for term in ['windows', 'mac', 'apple', 'microsoft', 'dell', 'hp', 'lenovo', 'asus']:
                if term in ' '.join(label_types).lower() or term in ' '.join(web_descriptions).lower():
                    if term not in ' '.join(product_terms).lower():
                        product_terms.append(term)
            
            # Add operating system info if detected
            if 'windows' in ' '.join(label_types).lower() or 'windows' in ' '.join(web_descriptions).lower():
                if 'windows' not in ' '.join(product_terms).lower():
                    product_terms.append('Windows')
            
            # Translate to Japanese search terms if needed
            japanese_terms = []
            for term in product_terms:
                if term.lower() == 'laptop':
                    japanese_terms.append('ノートパソコン')
                elif term.lower() == 'computer':
                    japanese_terms.append('コンピュータ')
                elif term.lower() == 'notebook':
                    japanese_terms.append('ノートブック')
                elif term.lower() == 'pc':
                    japanese_terms.append('PC')
                elif term.lower() == 'windows':
                    japanese_terms.append('Windows')
                else:
                    japanese_terms.append(term)
            
            # Construct final search term
            if japanese_terms:
                final_term = ' '.join(japanese_terms)
                print(f"Analyzed image content: {final_term}")
                return final_term
            
            # Fallback to the original method if nothing specific is found
            return self._generate_japanese_search_term(labels, objects)
            
        except Exception as e:
            print(f"Error in _generate_detailed_search_term: {e}")
            return self._generate_japanese_search_term(labels, objects) 
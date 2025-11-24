import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Search, TrendingUp, AlertCircle, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";

interface ResearchResult {
  success: boolean;
  jp_amazon?: {
    asin: string;
    title: string;
    price: number;
    price_currency: string;
    image_url?: string;
    url?: string;
    description?: string;
    availability?: boolean;
  };
  us_amazon?: {
    asin: string;
    title: string;
    price: number;
    price_currency: string;
    price_jpy: number;
    image_url?: string;
    url?: string;
    description?: string;
    availability?: boolean;
  };
  price_difference?: {
    amount_jpy: number;
    percent: number;
    exchange_rate_used: number;
  };
  error?: string;
}

export default function Research() {
  const [asin, setAsin] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const handleSearch = async () => {
    if (!asin.trim()) {
      toast({
        title: "エラー",
        description: "ASINを入力してください",
        variant: "destructive",
      });
      return;
    }

    // Validate ASIN format (alphanumeric, 10 characters)
    if (!/^[A-Z0-9]{10}$/.test(asin.trim())) {
      toast({
        title: "エラー",
        description: "有効なASINを入力してください（10文字の英数字）",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch("/api/compare/us-jp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          asin: asin.trim(),
          us_asin: asin.trim(),
          exchange_rate: 150.0, // Default exchange rate, could be made configurable
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "検索に失敗しました");
      }

      const data: ResearchResult = await response.json();
      
      if (data.success) {
        setResults(data);
        toast({
          title: "成功",
          description: "商品情報を取得しました",
        });
      } else {
        throw new Error(data.error || "検索に失敗しました");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "検索中にエラーが発生しました";
      setError(errorMessage);
      toast({
        title: "エラー",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !loading) {
      handleSearch();
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">商品リサーチ</h1>
        <p className="text-muted-foreground mt-1">
          日米Amazon価格差を計算し、利益商品を発見
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>ASIN検索</CardTitle>
          <CardDescription>
            Amazon USのASINを入力して価格差と利益を確認
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="flex-1 space-y-2">
                <Label htmlFor="asin">Amazon US ASIN</Label>
                <Input
                  id="asin"
                  placeholder="例: B08N5WRWNW"
                  value={asin}
                  onChange={(e) => setAsin(e.target.value.toUpperCase())}
                  onKeyPress={handleKeyPress}
                  className="font-mono"
                  disabled={loading}
                />
              </div>
              <div className="flex items-end">
                <Button 
                  className="w-32" 
                  onClick={handleSearch}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      検索中...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" />
                      検索
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div className="bg-muted/50 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <AlertCircle className="h-4 w-4" />
                <span>ASINを入力すると、以下の情報が自動計算されます：</span>
              </div>
              <ul className="text-sm text-muted-foreground space-y-1 ml-6">
                <li>• 米国Amazonの価格と在庫状況</li>
                <li>• 日本Amazonでの販売価格</li>
                <li>• 国際送料・関税・手数料を含む総コスト</li>
                <li>• 予想利益額と利益率</li>
                <li>• 出品規制・危険物の自動判定</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>検索結果</CardTitle>
          <CardDescription>商品情報と利益計算</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12">
              <Loader2 className="h-12 w-12 mx-auto text-muted-foreground mb-4 animate-spin" />
              <p className="text-muted-foreground">
                商品情報を取得しています...
              </p>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
              <p className="text-destructive font-medium mb-2">エラーが発生しました</p>
              <p className="text-muted-foreground text-sm">{error}</p>
            </div>
          ) : results ? (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">米国Amazon</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {results.us_amazon?.image_url && (
                      <div className="w-full aspect-square overflow-hidden rounded-lg bg-muted flex items-center justify-center">
                        <img 
                          src={results.us_amazon.image_url} 
                          alt={results.us_amazon.title || "Product image"}
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      </div>
                    )}
                    {results.us_amazon?.title && (
                      <div>
                        <p className="font-medium text-sm leading-tight">{results.us_amazon.title}</p>
                        {results.us_amazon.url && (
                          <a 
                            href={results.us_amazon.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline mt-1 inline-block"
                          >
                            商品ページを見る →
                          </a>
                        )}
                      </div>
                    )}
                    <div className="space-y-1">
                      <div className="flex items-baseline gap-2">
                        {results.us_amazon?.price && (
                          <>
                            <span className="text-2xl font-bold">
                              ${results.us_amazon.price.toFixed(2)}
                            </span>
                            <span className="text-sm text-muted-foreground">USD</span>
                          </>
                        )}
                      </div>
                      {results.us_amazon?.price_jpy && (
                        <p className="text-sm text-muted-foreground">
                          ≈ ¥{results.us_amazon.price_jpy.toLocaleString('ja-JP')}
                        </p>
                      )}
                    </div>
                    {results.us_amazon?.description && (
                      <div className="text-xs text-muted-foreground line-clamp-3">
                        {results.us_amazon.description}
                      </div>
                    )}
                    {results.us_amazon?.availability !== undefined && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className={`w-2 h-2 rounded-full ${
                          results.us_amazon.availability ? 'bg-green-500' : 'bg-red-500'
                        }`}></span>
                        <span className="text-muted-foreground">
                          {results.us_amazon.availability ? '在庫あり' : '在庫なし'}
                        </span>
                      </div>
                    )}
                    {results.us_amazon?.asin && (
                      <p className="text-xs text-muted-foreground font-mono">
                        ASIN: {results.us_amazon.asin}
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">日本Amazon</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {results.jp_amazon?.image_url && (
                      <div className="w-full aspect-square overflow-hidden rounded-lg bg-muted flex items-center justify-center">
                        <img 
                          src={results.jp_amazon.image_url} 
                          alt={results.jp_amazon.title || "Product image"}
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      </div>
                    )}
                    {results.jp_amazon?.title && (
                      <div>
                        <p className="font-medium text-sm leading-tight">{results.jp_amazon.title}</p>
                        {results.jp_amazon.url && (
                          <a 
                            href={results.jp_amazon.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline mt-1 inline-block"
                          >
                            商品ページを見る →
                          </a>
                        )}
                      </div>
                    )}
                    {results.jp_amazon?.price ? (
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold">
                          ¥{results.jp_amazon.price.toLocaleString('ja-JP')}
                        </span>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">商品が見つかりませんでした</p>
                    )}
                    {results.jp_amazon?.description && (
                      <div className="text-xs text-muted-foreground line-clamp-3">
                        {results.jp_amazon.description}
                      </div>
                    )}
                    {results.jp_amazon?.availability !== undefined && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className={`w-2 h-2 rounded-full ${
                          results.jp_amazon.availability ? 'bg-green-500' : 'bg-red-500'
                        }`}></span>
                        <span className="text-muted-foreground">
                          {results.jp_amazon.availability ? '在庫あり' : '在庫なし'}
                        </span>
                      </div>
                    )}
                    {results.jp_amazon?.asin && (
                      <p className="text-xs text-muted-foreground font-mono">
                        ASIN: {results.jp_amazon.asin}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {results.price_difference && results.us_amazon?.price && results.jp_amazon?.price && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">利益分析</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-baseline gap-2">
                      <span className={`text-3xl font-bold ${
                        results.price_difference.amount_jpy > 0 ? 'text-success' : 'text-destructive'
                      }`}>
                        ¥{results.price_difference.amount_jpy.toLocaleString('ja-JP')}
                      </span>
                      <span className="text-sm text-muted-foreground">予想利益額</span>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">為替レート:</span>
                        <span className="font-medium">¥{results.price_difference.exchange_rate_used}/USD</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">利益率:</span>
                        <span className={`font-medium ${
                          results.price_difference.percent > 0 ? 'text-success' : 'text-destructive'
                        }`}>
                          {results.price_difference.percent.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                ASINを入力して検索してください
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">推奨利益額</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-success">¥3,000</span>
              <span className="text-sm text-muted-foreground">以上</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              新規アカウント推奨範囲
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">推奨利益率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-info">15%</span>
              <span className="text-sm text-muted-foreground">以上</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              安定運用のための目標
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">リスクレベル</CardTitle>
          </CardHeader>
          <CardContent>
            <Badge className="bg-success">低リスク推奨</Badge>
            <p className="text-xs text-muted-foreground mt-2">
              新規アカウント向けカテゴリ
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

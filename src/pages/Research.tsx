import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Search, TrendingUp, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function Research() {
  const [asin, setAsin] = useState("");

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
                  className="font-mono"
                />
              </div>
              <div className="flex items-end">
                <Button className="w-32">
                  <Search className="h-4 w-4 mr-2" />
                  検索
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
          <div className="text-center py-12">
            <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              ASINを入力して検索してください
            </p>
          </div>
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

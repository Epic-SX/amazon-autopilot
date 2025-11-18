import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Shield, Plus, Trash2, AlertTriangle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function Blacklist() {
  const [newAsin, setNewAsin] = useState("");
  const [newBrand, setNewBrand] = useState("");
  const [newKeyword, setNewKeyword] = useState("");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">ブラックリスト管理</h1>
        <p className="text-muted-foreground mt-1">
          リスクの高い商品を自動除外
        </p>
      </div>

      <Card className="border-warning">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-warning">
            <AlertTriangle className="h-5 w-5" />
            重要なお知らせ
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            ブラックリストに登録された商品は、リサーチ時と出品時に自動的に除外されます。
            新規アカウントのリスクを最小化するため、初期状態で高リスク商品が登録されています。
          </p>
        </CardContent>
      </Card>

      <Tabs defaultValue="asins" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="asins">禁止ASIN</TabsTrigger>
          <TabsTrigger value="brands">NGブランド</TabsTrigger>
          <TabsTrigger value="keywords">NGキーワード</TabsTrigger>
        </TabsList>

        <TabsContent value="asins" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>ASINを追加</CardTitle>
              <CardDescription>
                出品禁止のASINを個別に登録
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <div className="flex-1">
                  <Input
                    placeholder="例: B08N5WRWNW"
                    value={newAsin}
                    onChange={(e) => setNewAsin(e.target.value.toUpperCase())}
                    className="font-mono"
                  />
                </div>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  追加
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>登録済みASIN</CardTitle>
              <CardDescription>現在ブラックリストに登録されているASIN</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {["B08N5WRWNW", "B09XYZABC1"].map((asin) => (
                  <div
                    key={asin}
                    className="flex items-center justify-between p-3 rounded-lg border"
                  >
                    <span className="font-mono text-sm">{asin}</span>
                    <Button variant="ghost" size="icon">
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="brands" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>ブランドを追加</CardTitle>
              <CardDescription>
                出品禁止のブランド・メーカー名を登録
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <div className="flex-1">
                  <Input
                    placeholder="例: Sony, Apple"
                    value={newBrand}
                    onChange={(e) => setNewBrand(e.target.value)}
                  />
                </div>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  追加
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>登録済みブランド</CardTitle>
              <CardDescription>高リスクブランド一覧</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {["Apple", "Sony", "Nintendo", "LEGO", "Disney"].map((brand) => (
                  <Badge key={brand} variant="secondary" className="px-3 py-1.5">
                    {brand}
                    <button className="ml-2 hover:text-destructive">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="keywords" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>キーワードを追加</CardTitle>
              <CardDescription>
                商品名に含まれると除外されるキーワード
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Textarea
                  placeholder="1行につき1キーワード&#10;例:&#10;危険物&#10;バッテリー&#10;液体"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  rows={5}
                />
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  一括追加
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>登録済みキーワード</CardTitle>
              <CardDescription>除外キーワード一覧</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {["バッテリー", "液体", "危険物", "化粧品", "食品"].map((keyword) => (
                  <Badge key={keyword} variant="outline" className="px-3 py-1.5">
                    {keyword}
                    <button className="ml-2 hover:text-destructive">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            自動判定機能
          </CardTitle>
          <CardDescription>
            以下の商品は自動的に除外されます
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-destructive" />
              Amazon危険物（Hazmat）判定商品
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-destructive" />
              出品規制カテゴリ商品
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-destructive" />
              メーカー直販・大手ブランド
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-destructive" />
              返品率の高いカテゴリ
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

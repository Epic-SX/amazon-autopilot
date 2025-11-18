import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Key, Database, DollarSign, Truck } from "lucide-react";

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">設定</h1>
        <p className="text-muted-foreground mt-1">
          システム全体の設定を管理
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5 text-primary" />
            Amazon SP-API設定
          </CardTitle>
          <CardDescription>
            Amazon APIへの接続情報を設定
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="sp-api-key">SP-API アクセスキー</Label>
            <Input
              id="sp-api-key"
              type="password"
              placeholder="未設定"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="sp-api-secret">SP-API シークレットキー</Label>
            <Input
              id="sp-api-secret"
              type="password"
              placeholder="未設定"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="seller-id">セラーID</Label>
            <Input
              id="seller-id"
              placeholder="未設定"
            />
          </div>
          <Button>API設定を保存</Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5 text-primary" />
              送料計算
            </CardTitle>
            <CardDescription>
              国際送料の計算方法を選択
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="shipping-provider">送料計算サービス</Label>
              <Select defaultValue="madbeast">
                <SelectTrigger id="shipping-provider">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="madbeast">マッドビースト</SelectItem>
                  <SelectItem value="yunyu-com">輸入コム</SelectItem>
                  <SelectItem value="manual">手動設定</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="shipping-api">APIキー</Label>
              <Input
                id="shipping-api"
                type="password"
                placeholder="未設定"
              />
            </div>
            <Button variant="secondary">送料設定を保存</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-primary" />
              為替レート
            </CardTitle>
            <CardDescription>
              USD/JPY為替の取得設定
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="exchange-rate">現在の為替レート</Label>
              <Input
                id="exchange-rate"
                type="number"
                defaultValue="150.50"
                step="0.01"
              />
              <p className="text-xs text-muted-foreground">
                自動取得または手動設定
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rate-margin">為替マージン（%）</Label>
              <Input
                id="rate-margin"
                type="number"
                defaultValue="2"
                min="0"
                max="10"
              />
              <p className="text-xs text-muted-foreground">
                変動リスク対策のマージン
              </p>
            </div>
            <Button variant="secondary">為替設定を保存</Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            データ管理
          </CardTitle>
          <CardDescription>
            商品データのバックアップと管理
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <div className="font-medium">データベースのバックアップ</div>
              <div className="text-sm text-muted-foreground">
                最終バックアップ: 未実施
              </div>
            </div>
            <Button variant="outline">今すぐバックアップ</Button>
          </div>
          <div className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <div className="font-medium">データのエクスポート</div>
              <div className="text-sm text-muted-foreground">
                全商品データをCSVで出力
              </div>
            </div>
            <Button variant="outline">エクスポート</Button>
          </div>
          <div className="flex items-center justify-between p-4 rounded-lg border border-destructive">
            <div>
              <div className="font-medium text-destructive">全データを削除</div>
              <div className="text-sm text-muted-foreground">
                この操作は取り消せません
              </div>
            </div>
            <Button variant="destructive">削除</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

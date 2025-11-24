import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Activity, DollarSign, Package, Loader2 } from "lucide-react";
import { monitoringApi } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function Monitoring() {
  const [monitorStatus, setMonitorStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadMonitorStatus();
  }, []);

  const loadMonitorStatus = async () => {
    try {
      setLoading(true);
      const response = await monitoringApi.getStatus();
      if (response.success) {
        setMonitorStatus(response);
      }
    } catch (error) {
      console.error('Failed to load monitor status:', error);
      toast({
        title: "エラー",
        description: "監視ステータスの読み込みに失敗しました",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCheckAll = async () => {
    try {
      setChecking(true);
      const response = await monitoringApi.checkAll();
      if (response.success) {
        toast({
          title: "成功",
          description: "全商品の在庫チェックを実行しました",
        });
        loadMonitorStatus();
      }
    } catch (error) {
      console.error('Failed to check all listings:', error);
      toast({
        title: "エラー",
        description: "在庫チェックに失敗しました",
        variant: "destructive",
      });
    } finally {
      setChecking(false);
    }
  };
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">監視設定</h1>
        <p className="text-muted-foreground mt-1">
          24時間自動監視と価格改定の設定
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              在庫監視
            </CardTitle>
            <CardDescription>
              仕入れ先の在庫状況を自動で監視
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="stock-monitor" className="flex-1">
                <div className="font-medium">在庫監視を有効化</div>
                <div className="text-sm text-muted-foreground">
                  在庫切れ時に自動停止
                </div>
              </Label>
              <Switch id="stock-monitor" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="check-interval">監視間隔（分）</Label>
              <Input
                id="check-interval"
                type="number"
                defaultValue="30"
                min="15"
                max="240"
              />
              <p className="text-xs text-muted-foreground">
                15〜240分の範囲で設定可能
              </p>
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="auto-pause" className="flex-1">
                <div className="font-medium">自動停止</div>
                <div className="text-sm text-muted-foreground">
                  在庫切れ商品を自動で停止
                </div>
              </Label>
              <Switch id="auto-pause" defaultChecked />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-primary" />
              価格改定
            </CardTitle>
            <CardDescription>
              価格変動の自動反映設定
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="price-monitor" className="flex-1">
                <div className="font-medium">価格監視を有効化</div>
                <div className="text-sm text-muted-foreground">
                  仕入れ価格の変動を追跡
                </div>
              </Label>
              <Switch id="price-monitor" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="min-profit">最低利益額（円）</Label>
              <Input
                id="min-profit"
                type="number"
                defaultValue="3000"
                min="0"
              />
              <p className="text-xs text-muted-foreground">
                この金額以下の商品は自動停止
              </p>
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="auto-reprice" className="flex-1">
                <div className="font-medium">自動価格改定</div>
                <div className="text-sm text-muted-foreground">
                  価格を自動で更新
                </div>
              </Label>
              <Switch id="auto-reprice" defaultChecked />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-primary" />
            出品管理
          </CardTitle>
          <CardDescription>
            新規アカウント向けの安全設定
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="daily-limit">1日の最大出品数</Label>
            <Input
              id="daily-limit"
              type="number"
              defaultValue="20"
              min="1"
              max="100"
            />
            <p className="text-xs text-muted-foreground">
              新規アカウントは20品/日を推奨
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="max-products">最大商品数</Label>
            <Input
              id="max-products"
              type="number"
              defaultValue="1000"
              min="100"
            />
            <p className="text-xs text-muted-foreground">
              新規アカウントは300〜1,000品を推奨
            </p>
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="safe-mode" className="flex-1">
              <div className="font-medium">セーフモード</div>
              <div className="text-sm text-muted-foreground">
                新規アカウント向けの安全運用
              </div>
            </Label>
            <Switch id="safe-mode" defaultChecked />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>監視ステータス</CardTitle>
          <CardDescription>現在の監視システムの状態</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : monitorStatus ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="p-4 rounded-lg border">
                  <div className="text-sm text-muted-foreground mb-1">監視中</div>
                  <div className="text-2xl font-bold">{monitorStatus.monitoring_count || 0}件</div>
                </div>
                <div className="p-4 rounded-lg border">
                  <div className="text-sm text-muted-foreground mb-1">最終チェック</div>
                  <div className="text-sm font-medium">
                    {monitorStatus.last_check_time ? 
                      new Date(monitorStatus.last_check_time).toLocaleString('ja-JP') : 
                      '未実行'}
                  </div>
                </div>
              </div>
              <Button 
                onClick={handleCheckAll} 
                disabled={checking}
                className="w-full"
              >
                {checking ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    チェック中...
                  </>
                ) : (
                  '全商品を今すぐチェック'
                )}
              </Button>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              監視ステータスの情報がありません
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button size="lg" onClick={() => loadMonitorStatus()}>
          設定を保存
        </Button>
      </div>
    </div>
  );
}

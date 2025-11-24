import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Shield, Plus, Trash2, AlertTriangle, Loader2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { blacklistApi } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface BlacklistEntryItem {
  id: string;
  value: string;
  reason?: string;
  severity?: string;
  type: string;
}

interface BlacklistState {
  asins: BlacklistEntryItem[];
  brands: BlacklistEntryItem[];
  keywords: BlacklistEntryItem[];
}

export default function Blacklist() {
  const [newAsin, setNewAsin] = useState("");
  const [newBrand, setNewBrand] = useState("");
  const [newKeyword, setNewKeyword] = useState("");
  const [blacklist, setBlacklist] = useState<BlacklistState | null>(null);
  const [loading, setLoading] = useState(true);
  const [processingAction, setProcessingAction] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadBlacklist();
  }, []);

  const loadBlacklist = async () => {
    try {
      setLoading(true);
      const response = await blacklistApi.getAll();
      if (response.success) {
        const entries = response.entries || [];
        const toEntry = (entry: any): BlacklistEntryItem => ({
          id: entry.entry_id,
          value: entry.value,
          reason: entry.reason,
          severity: entry.severity,
          type: entry.entry_type,
        });

        const transformed: BlacklistState = {
          asins: entries.filter((e: any) => e.entry_type === 'asin').map(toEntry),
          brands: entries
            .filter((e: any) => e.entry_type === 'brand' || e.entry_type === 'manufacturer')
            .map(toEntry),
          keywords: entries.filter((e: any) => e.entry_type === 'keyword').map(toEntry),
        };
        setBlacklist(transformed);
      }
    } catch (error) {
      console.error('Failed to load blacklist:', error);
      toast({
        title: "エラー",
        description: "ブラックリストの読み込みに失敗しました",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const isProcessing = (action: string) => processingAction === action;

  const handleCheckAsin = async () => {
    if (!newAsin.trim()) {
      toast({
        title: "エラー",
        description: "ASINを入力してください",
        variant: "destructive",
      });
      return;
    }
    try {
      setProcessingAction("check");
      const response = await blacklistApi.check({ asin: newAsin.trim() });
      if (response.success && response.result && response.result.is_blacklisted) {
        toast({
          title: "警告",
          description: `ASIN ${newAsin} はブラックリストに登録されています`,
          variant: "destructive",
        });
      } else {
        toast({
          title: "確認",
          description: `ASIN ${newAsin} はブラックリストに登録されていません`,
        });
      }
    } catch (error) {
      console.error('Failed to check ASIN:', error);
      toast({
        title: "エラー",
        description: "ASINのチェックに失敗しました",
        variant: "destructive",
      });
    } finally {
      setProcessingAction(null);
    }
  };

  const handleAddEntries = async (type: 'asin' | 'brand' | 'keyword', values: string[]) => {
    const cleanedValues = values
      .map((value) => value.trim())
      .filter((value) => value.length > 0);

    if (cleanedValues.length === 0) {
      toast({
        title: "エラー",
        description: "追加する内容を入力してください",
        variant: "destructive",
      });
      return;
    }

    const defaultReasons = {
      asin: "手動で登録されたASIN",
      brand: "手動で登録されたブランド",
      keyword: "手動で登録されたキーワード",
    };

    try {
      setProcessingAction(`add-${type}`);
      for (const value of cleanedValues) {
        await blacklistApi.create({
          type,
          value,
          reason: defaultReasons[type],
          severity: type === 'keyword' ? 'medium' : 'high',
        });
      }

      toast({
        title: "成功",
        description: `${cleanedValues.length}件を追加しました`,
      });

      if (type === 'asin') setNewAsin("");
      if (type === 'brand') setNewBrand("");
      if (type === 'keyword') setNewKeyword("");

      loadBlacklist();
    } catch (error) {
      console.error('Failed to add blacklist entry:', error);
      toast({
        title: "エラー",
        description: "ブラックリストの追加に失敗しました",
        variant: "destructive",
      });
    } finally {
      setProcessingAction(null);
    }
  };

  const handleDeleteEntry = async (entryId: string) => {
    try {
      setDeletingId(entryId);
      await blacklistApi.delete(entryId);
      toast({
        title: "成功",
        description: "ブラックリストから削除しました",
      });
      loadBlacklist();
    } catch (error) {
      console.error('Failed to delete blacklist entry:', error);
      toast({
        title: "エラー",
        description: "ブラックリストの削除に失敗しました",
        variant: "destructive",
      });
    } finally {
      setDeletingId(null);
    }
  };

  const handleAddAsin = () => handleAddEntries('asin', [newAsin.toUpperCase()]);
  const handleAddBrand = () => handleAddEntries('brand', [newBrand]);
  const handleAddKeywords = () => handleAddEntries('keyword', newKeyword.split(/\r?\n|,|、/));

  const renderDeleteButton = (entryId: string) => (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => handleDeleteEntry(entryId)}
      disabled={deletingId === entryId}
    >
      {deletingId === entryId ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Trash2 className="h-4 w-4 text-destructive" />
      )}
    </Button>
  );

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
                <Button onClick={handleAddAsin} disabled={isProcessing('add-asin')}>
                  {isProcessing('add-asin') ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      追加中...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      追加
                    </>
                  )}
                </Button>
                <Button variant="secondary" onClick={handleCheckAsin} disabled={isProcessing('check')}>
                  {isProcessing('check') ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      チェック中...
                    </>
                  ) : (
                    <>
                      チェック
                    </>
                  )}
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
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-2">
                  {blacklist?.asins && blacklist.asins.length > 0 ? (
                    blacklist.asins.map((entry) => (
                      <div
                        key={entry.id}
                        className="flex items-center justify-between p-3 rounded-lg border"
                      >
                        <div>
                          <span className="font-mono text-sm">{entry.value.toUpperCase()}</span>
                          {entry.reason && (
                            <p className="text-xs text-muted-foreground mt-1">{entry.reason}</p>
                          )}
                        </div>
                        {renderDeleteButton(entry.id)}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      ブラックリストに登録されているASINはありません
                    </div>
                  )}
                </div>
              )}
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
                  <Button onClick={handleAddBrand} disabled={isProcessing('add-brand')}>
                    {isProcessing('add-brand') ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        追加中...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        追加
                      </>
                    )}
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
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {blacklist?.brands && blacklist.brands.length > 0 ? (
                    blacklist.brands.map((brand) => (
                      <Badge key={brand.id} variant="secondary" className="px-3 py-1.5 flex items-center gap-2">
                        <span>{brand.value}</span>
                        <button
                          className="ml-2 hover:text-destructive flex items-center"
                          onClick={() => handleDeleteEntry(brand.id)}
                          disabled={deletingId === brand.id}
                        >
                          {deletingId === brand.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Trash2 className="h-3 w-3" />
                          )}
                        </button>
                      </Badge>
                    ))
                  ) : (
                    <p className="text-muted-foreground">登録されたブランドはありません</p>
                  )}
                </div>
              )}
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
                <Button onClick={handleAddKeywords} disabled={isProcessing('add-keyword')}>
                  {isProcessing('add-keyword') ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      追加中...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      一括追加
                    </>
                  )}
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
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {blacklist?.keywords && blacklist.keywords.length > 0 ? (
                    blacklist.keywords.map((keyword) => (
                      <Badge key={keyword.id} variant="outline" className="px-3 py-1.5 flex items-center gap-2">
                        <span>{keyword.value}</span>
                        <button
                          className="ml-2 hover:text-destructive flex items-center"
                          onClick={() => handleDeleteEntry(keyword.id)}
                          disabled={deletingId === keyword.id}
                        >
                          {deletingId === keyword.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Trash2 className="h-3 w-3" />
                          )}
                        </button>
                      </Badge>
                    ))
                  ) : (
                    <p className="text-muted-foreground">登録されたキーワードはありません</p>
                  )}
                </div>
              )}
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

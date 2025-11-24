import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Upload, Download, Pause, Play, Trash2, Package, Loader2 } from "lucide-react";
import { listingsApi, ApiError } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

interface Listing {
  id: string;
  asin: string;
  title: string;
  listing_price: number;
  profit?: number;
  status: string;
  stock_status?: string;
  jp_price?: number;
  us_price?: number;
}

interface ListingFormData {
  asin: string;
  jp_asin: string;
  us_asin: string;
  title: string;
  listing_price: string;
  jp_price: string;
  us_price: string;
  category: string;
  manufacturer: string;
  source_url: string;
  minimum_profit_threshold: string;
}

const emptyFormState: ListingFormData = {
  asin: "",
  jp_asin: "",
  us_asin: "",
  title: "",
  listing_price: "",
  jp_price: "",
  us_price: "",
  category: "",
  manufacturer: "",
  source_url: "",
  minimum_profit_threshold: "3000",
};

export default function Products() {
  const [searchTerm, setSearchTerm] = useState("");
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState<ListingFormData>(emptyFormState);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof ListingFormData, string>>>({});
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadListings();
  }, []);

  const loadListings = async () => {
    try {
      setLoading(true);
      const response = await listingsApi.getAll();
      if (response.success && response.listings) {
        const normalized = response.listings.map((listing: any) => ({
          id: listing.listing_id,
          asin: listing.asin,
          title: listing.title,
          listing_price: listing.listing_price ?? 0,
          profit: listing.profit_amount,
          status: listing.status,
          stock_status: listing.stock_status,
          jp_price: listing.jp_price,
          us_price: listing.us_price,
        })) as Listing[];
        setListings(normalized);
      }
    } catch (error) {
      console.error('Failed to load listings:', error);
      toast({
        title: "エラー",
        description: "商品一覧の読み込みに失敗しました",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (listing: Listing) => {
    const newStatus = listing.status === 'active' ? 'paused' : 'active';
    try {
      setProcessingIds(prev => new Set(prev).add(listing.id));
      await listingsApi.update(listing.id, { status: newStatus });
      toast({
        title: "成功",
        description: `商品を${newStatus === 'active' ? '再開' : '停止'}しました`,
      });
      loadListings();
    } catch (error) {
      console.error('Failed to update listing:', error);
      toast({
        title: "エラー",
        description: "ステータスの更新に失敗しました",
        variant: "destructive",
      });
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev);
        next.delete(listing.id);
        return next;
      });
    }
  };

  const handleDelete = async (listingId: string) => {
    if (!confirm('この商品を削除してもよろしいですか？')) {
      return;
    }
    try {
      setProcessingIds(prev => new Set(prev).add(listingId));
      await listingsApi.delete(listingId);
      toast({
        title: "成功",
        description: "商品を削除しました",
      });
      loadListings();
    } catch (error) {
      console.error('Failed to delete listing:', error);
      toast({
        title: "エラー",
        description: "商品の削除に失敗しました",
        variant: "destructive",
      });
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev);
        next.delete(listingId);
        return next;
      });
    }
  };

  const handleInputChange = (field: keyof ListingFormData, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
    setFormErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const validateForm = () => {
    const errors: Partial<Record<keyof ListingFormData, string>> = {};
    if (!formData.asin.trim()) {
      errors.asin = "ASINは必須です";
    }
    if (!formData.title.trim()) {
      errors.title = "商品名は必須です";
    }
    if (!formData.listing_price.trim()) {
      errors.listing_price = "出品価格は必須です";
    }
    return errors;
  };

  const handleCreateListing = async (event?: React.FormEvent) => {
    event?.preventDefault();
    const errors = validateForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    const payload = {
      asin: formData.asin.trim(),
      jp_asin: formData.jp_asin.trim() || formData.asin.trim(),
      us_asin: formData.us_asin.trim() || undefined,
      title: formData.title.trim(),
      listing_price: Number(formData.listing_price) || 0,
      jp_price: Number(formData.jp_price) || 0,
      us_price: Number(formData.us_price) || 0,
      category: formData.category.trim() || undefined,
      manufacturer: formData.manufacturer.trim() || undefined,
      source_url: formData.source_url.trim() || undefined,
      minimum_profit_threshold: Number(formData.minimum_profit_threshold) || 3000,
      validate: true,
    };

    try {
      setCreating(true);
      const response = await listingsApi.create(payload);
      if (response.success) {
        toast({
          title: "成功",
          description: "商品を追加しました",
        });
        setAddDialogOpen(false);
        setFormData(emptyFormState);
        setFormErrors({});
        loadListings();
      } else {
        throw new Error("商品の追加に失敗しました");
      }
    } catch (error) {
      console.error('Failed to create listing:', error);
      let description = "商品の追加に失敗しました";
      if (error instanceof ApiError && Array.isArray(error.details?.errors)) {
        description = error.details?.errors.join('、');
      } else if (error instanceof Error && error.message) {
        description = error.message;
      }
      toast({
        title: "エラー",
        description,
        variant: "destructive",
      });
    } finally {
      setCreating(false);
    }
  };

  const filteredListings = listings.filter(listing => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      listing.asin.toLowerCase().includes(term) ||
      listing.title.toLowerCase().includes(term)
    );
  });

  const exportColumns = [
    { key: 'asin', label: 'ASIN' },
    { key: 'title', label: '商品名' },
    { key: 'listing_price', label: '出品価格 (JPY)' },
    { key: 'profit', label: '利益 (JPY)' },
    { key: 'status', label: 'ステータス' },
    { key: 'stock_status', label: '在庫ステータス' },
    { key: 'jp_price', label: '仕入れ価格 (JPY)' },
    { key: 'us_price', label: '仕入れ価格 (USD)' },
  ] as const;

  const handleExport = async () => {
    if (!listings.length) {
      toast({
        title: "情報",
        description: "出力できる商品がありません",
      });
      return;
    }

    try {
      setExporting(true);
      const header = exportColumns.map((column) => column.label);

      const escapeCsv = (value: unknown) => {
        if (value === null || value === undefined) return '""';
        const stringValue = String(value).replace(/"/g, '""');
        return `"${stringValue}"`;
      };

      const rows = listings.map((listing) =>
        exportColumns
          .map((column) => {
            const value = (listing as Record<string, unknown>)[column.key as keyof Listing];
            return escapeCsv(value ?? "");
          })
          .join(",")
      );

      const csvContent = [header.join(","), ...rows].join("\n");
      const csvWithBom = '\ufeff' + csvContent;
      const blob = new Blob([csvWithBom], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `listings_${new Date().toISOString()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: "成功",
        description: "CSVをダウンロードしました",
      });
    } catch (error) {
      console.error("Failed to export listings:", error);
      toast({
        title: "エラー",
        description: "CSVの出力に失敗しました",
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  const handleImportClick = () => {
    if (importing) return;
    fileInputRef.current?.click();
  };

  const parseImportedData = (text: string) => {
    text = text.trim();
    if (!text) return [];

    try {
      const json = JSON.parse(text);
      if (Array.isArray(json)) {
        return json;
      }
      if (typeof json === "object") {
        return [json];
      }
    } catch {
      // Fallback to CSV parsing
    }

    const lines = text.split(/\r?\n/).filter((line) => line.trim());
    if (!lines.length) return [];

    const headerMappings: Record<string, string> = {
      asin: 'asin',
      ASIN: 'asin',
      title: 'title',
      商品名: 'title',
      'listing_price': 'listing_price',
      'listing_pri': 'listing_price',
      'listing_price (JPY)': 'listing_price',
      '出品価格': 'listing_price',
      '出品価格 (JPY)': 'listing_price',
      profit: 'profit',
      利益: 'profit',
      'status': 'status',
      'ステータス': 'status',
      'stock_status': 'stock_status',
      'stock_stat': 'stock_status',
      '在庫ステータス': 'stock_status',
      'jp_price': 'jp_price',
      '仕入れ価格 (JPY)': 'jp_price',
      'us_price': 'us_price',
      '仕入れ価格 (USD)': 'us_price',
    };

    const headers = lines[0].split(",").map((header) => {
      const cleaned = header.replace(/^"|"$/g, "").trim();
      return headerMappings[cleaned] || cleaned;
    });
    const records: Record<string, string>[] = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i]
        .match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g)
        ?.map((value) => value.replace(/^"|"$/g, "").replace(/""/g, '"').trim()) ?? [];

      if (values.length === 0) continue;

      const record: Record<string, string> = {};
      headers.forEach((header, index) => {
        record[header] = values[index] ?? "";
      });
      records.push(record);
    }

    return records;
  };

  const handleImportFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setImporting(true);
      const text = await file.text();
      const records = parseImportedData(text);

      if (!records.length) {
        toast({
          title: "注意",
          description: "読み込めるデータがありませんでした",
        });
        return;
      }

      const createPayload = (record: any) => {
        const asin = record.asin?.trim();
        const title = record.title?.trim();
        const listingPrice = record.listing_price ?? record.listingPrice;

        if (!asin || !title || (!listingPrice && listingPrice !== 0)) {
          return null;
        }

        return {
          asin,
          jp_asin: record.jp_asin?.trim() || asin,
          us_asin: record.us_asin?.trim() || undefined,
          title,
          listing_price: Number(listingPrice) || 0,
          jp_price: Number(record.jp_price ?? record.jpPrice) || 0,
          us_price: Number(record.us_price ?? record.usPrice) || 0,
          category: record.category?.trim() || undefined,
          manufacturer: record.manufacturer?.trim() || undefined,
          source_url: record.source_url?.trim() || record.sourceUrl?.trim() || undefined,
          minimum_profit_threshold: Number(record.minimum_profit_threshold ?? record.minimumProfitThreshold) || 3000,
          validate: true,
        };
      };

      const payloads = records
        .map(createPayload)
        .filter((payload): payload is NonNullable<typeof payload> => Boolean(payload));

      if (!payloads.length) {
        toast({
          title: "注意",
          description: "必須項目 (ASIN, 商品名, 出品価格) が揃っている行がありませんでした",
        });
        return;
      }

      const results = await Promise.allSettled(payloads.map((payload) => listingsApi.create(payload)));
      const successCount = results.filter((result) => result.status === "fulfilled" && (result.value as any)?.success).length;
      const failedCount = payloads.length - successCount;

      toast({
        title: "インポート完了",
        description: `${successCount}件の商品の追加に成功${failedCount ? `、${failedCount}件に失敗` : ''}しました`,
        variant: failedCount ? "destructive" : "default",
      });

      if (successCount) {
        loadListings();
      }
    } catch (error) {
      console.error("Failed to import listings:", error);
      toast({
        title: "エラー",
        description: "商品のインポートに失敗しました",
        variant: "destructive",
      });
    } finally {
      setImporting(false);
      event.target.value = "";
    }
  };

  return (
    <div className="space-y-6">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.json,text/csv,application/json"
        className="hidden"
        onChange={handleImportFile}
      />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">商品管理</h1>
          <p className="text-muted-foreground mt-1">
            出品商品の追加・編集・削除を管理
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting || loading}>
            {exporting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
            エクスポート
          </Button>
          <Button variant="outline" size="sm" onClick={handleImportClick} disabled={importing}>
            {importing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Upload className="h-4 w-4 mr-2" />}
            インポート
          </Button>
          <Button size="sm" onClick={() => setAddDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            商品追加
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>出品中の商品</CardTitle>
          <CardDescription>現在Amazonに出品されている商品一覧</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="ASIN、商品名で検索..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button variant="secondary" onClick={() => loadListings()}>
                <Search className="h-4 w-4 mr-2" />
                検索
              </Button>
            </div>

            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ASIN</TableHead>
                    <TableHead>商品名</TableHead>
                    <TableHead>価格</TableHead>
                    <TableHead>利益</TableHead>
                    <TableHead>在庫</TableHead>
                    <TableHead>ステータス</TableHead>
                    <TableHead className="text-right">アクション</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  ) : filteredListings.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        商品が見つかりませんでした
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredListings.map((listing) => (
                      <TableRow key={listing.id}>
                        <TableCell className="font-mono text-sm">{listing.asin}</TableCell>
                        <TableCell>{listing.title}</TableCell>
                        <TableCell>¥{listing.listing_price?.toLocaleString('ja-JP') || 'N/A'}</TableCell>
                        <TableCell className="text-success font-medium">
                          ¥{listing.profit?.toLocaleString('ja-JP') || 'N/A'}
                        </TableCell>
                        <TableCell>
                          {listing.stock_status === 'in_stock' ? '在庫あり' : 
                           listing.stock_status === 'out_of_stock' ? '在庫切れ' : 
                           '不明'}
                        </TableCell>
                        <TableCell>
                          {listing.status === "active" ? (
                            <Badge className="bg-success">出品中</Badge>
                          ) : (
                            <Badge variant="secondary">停止中</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button 
                              variant="ghost" 
                              size="icon"
                              onClick={() => handleToggleStatus(listing)}
                              disabled={processingIds.has(listing.id)}
                            >
                              {processingIds.has(listing.id) ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : listing.status === "active" ? (
                                <Pause className="h-4 w-4" />
                              ) : (
                                <Play className="h-4 w-4" />
                              )}
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon"
                              onClick={() => handleDelete(listing.id)}
                              disabled={processingIds.has(listing.id)}
                            >
                              {processingIds.has(listing.id) ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4 text-destructive" />
                              )}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {!loading && filteredListings.length === 0 && (
              <div className="text-center py-12">
                <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">商品がまだ登録されていません</p>
                <Button className="mt-4" size="sm" onClick={() => setAddDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  最初の商品を追加
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Dialog
        open={addDialogOpen}
        onOpenChange={(open) => {
          setAddDialogOpen(open);
          if (!open) {
            setFormData(emptyFormState);
            setFormErrors({});
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>商品を追加</DialogTitle>
            <DialogDescription>Amazonに登録したい商品の情報を入力してください。</DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={handleCreateListing}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="asin">ASIN *</Label>
                <Input
                  id="asin"
                  value={formData.asin}
                  onChange={(e) => handleInputChange('asin', e.target.value)}
                  placeholder="B00XXXXXXX"
                  required
                />
                {formErrors.asin && <p className="text-xs text-destructive mt-1">{formErrors.asin}</p>}
              </div>
              <div>
                <Label htmlFor="jp_asin">JP ASIN</Label>
                <Input
                  id="jp_asin"
                  value={formData.jp_asin}
                  onChange={(e) => handleInputChange('jp_asin', e.target.value)}
                  placeholder="未入力の場合はASINを使用"
                />
              </div>
              <div>
                <Label htmlFor="us_asin">US ASIN</Label>
                <Input
                  id="us_asin"
                  value={formData.us_asin}
                  onChange={(e) => handleInputChange('us_asin', e.target.value)}
                  placeholder="米国AmazonのASIN（任意）"
                />
              </div>
              <div>
                <Label htmlFor="title">商品名 *</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => handleInputChange('title', e.target.value)}
                  placeholder="商品タイトルを入力"
                  required
                />
                {formErrors.title && <p className="text-xs text-destructive mt-1">{formErrors.title}</p>}
              </div>
              <div>
                <Label htmlFor="listing_price">出品価格 (JPY) *</Label>
                <Input
                  id="listing_price"
                  type="number"
                  inputMode="decimal"
                  value={formData.listing_price}
                  onChange={(e) => handleInputChange('listing_price', e.target.value)}
                  placeholder="例: 9800"
                  required
                />
                {formErrors.listing_price && <p className="text-xs text-destructive mt-1">{formErrors.listing_price}</p>}
              </div>
              <div>
                <Label htmlFor="jp_price">仕入れ価格 (JPY)</Label>
                <Input
                  id="jp_price"
                  type="number"
                  inputMode="decimal"
                  value={formData.jp_price}
                  onChange={(e) => handleInputChange('jp_price', e.target.value)}
                  placeholder="日本での仕入れ価格"
                />
              </div>
              <div>
                <Label htmlFor="us_price">仕入れ価格 (USD)</Label>
                <Input
                  id="us_price"
                  type="number"
                  inputMode="decimal"
                  value={formData.us_price}
                  onChange={(e) => handleInputChange('us_price', e.target.value)}
                  placeholder="米国での仕入れ価格"
                />
              </div>
              <div>
                <Label htmlFor="category">カテゴリー</Label>
                <Input
                  id="category"
                  value={formData.category}
                  onChange={(e) => handleInputChange('category', e.target.value)}
                  placeholder="例: electronics"
                />
              </div>
              <div>
                <Label htmlFor="manufacturer">メーカー</Label>
                <Input
                  id="manufacturer"
                  value={formData.manufacturer}
                  onChange={(e) => handleInputChange('manufacturer', e.target.value)}
                  placeholder="メーカー名"
                />
              </div>
              <div>
                <Label htmlFor="source_url">仕入れ先URL</Label>
                <Input
                  id="source_url"
                  value={formData.source_url}
                  onChange={(e) => handleInputChange('source_url', e.target.value)}
                  placeholder="https://..."
                />
              </div>
              <div>
                <Label htmlFor="minimum_profit_threshold">最低利益 (JPY)</Label>
                <Input
                  id="minimum_profit_threshold"
                  type="number"
                  inputMode="decimal"
                  value={formData.minimum_profit_threshold}
                  onChange={(e) => handleInputChange('minimum_profit_threshold', e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setAddDialogOpen(false)}
                disabled={creating}
              >
                キャンセル
              </Button>
              <Button type="submit" disabled={creating}>
                {creating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                商品を追加
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

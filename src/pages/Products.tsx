import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Upload, Download, Pause, Play, Trash2, Package } from "lucide-react";

export default function Products() {
  const [searchTerm, setSearchTerm] = useState("");

  const sampleProducts = [
    {
      asin: "B08N5WRWNW",
      title: "サンプル商品1",
      price: "¥3,500",
      profit: "¥1,200",
      status: "active",
      stock: "在庫あり",
    },
    {
      asin: "B09XYZABC1",
      title: "サンプル商品2",
      price: "¥5,800",
      profit: "¥2,100",
      status: "paused",
      stock: "在庫切れ",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">商品管理</h1>
          <p className="text-muted-foreground mt-1">
            出品商品の追加・編集・削除を管理
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            エクスポート
          </Button>
          <Button variant="outline" size="sm">
            <Upload className="h-4 w-4 mr-2" />
            インポート
          </Button>
          <Button size="sm">
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
              <Button variant="secondary">検索</Button>
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
                  {sampleProducts.map((product) => (
                    <TableRow key={product.asin}>
                      <TableCell className="font-mono text-sm">{product.asin}</TableCell>
                      <TableCell>{product.title}</TableCell>
                      <TableCell>{product.price}</TableCell>
                      <TableCell className="text-success font-medium">{product.profit}</TableCell>
                      <TableCell>{product.stock}</TableCell>
                      <TableCell>
                        {product.status === "active" ? (
                          <Badge className="bg-success">出品中</Badge>
                        ) : (
                          <Badge variant="secondary">停止中</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon">
                            {product.status === "active" ? (
                              <Pause className="h-4 w-4" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </Button>
                          <Button variant="ghost" size="icon">
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {sampleProducts.length === 0 && (
              <div className="text-center py-12">
                <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">商品がまだ登録されていません</p>
                <Button className="mt-4" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  最初の商品を追加
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

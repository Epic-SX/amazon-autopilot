import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Package, TrendingUp, AlertTriangle, DollarSign, Loader2 } from "lucide-react";
import { listingsApi } from "@/lib/api";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const [stats, setStats] = useState({
    activeListings: 0,
    totalRevenue: 0,
    totalProfit: 0,
    outOfStock: 0,
  });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const response = await listingsApi.getAll();
      
      if (response.success && response.listings) {
        const listings = response.listings;
        const activeListings = listings.filter((l: any) => l.status === 'active');
        const outOfStock = listings.filter((l: any) => l.stock_status === 'out_of_stock');
        
        // Calculate revenue and profit (assuming we have these fields)
        const totalRevenue = listings.reduce((sum: number, l: any) => {
          return sum + (l.revenue || 0);
        }, 0);
        
        const totalProfit = listings.reduce((sum: number, l: any) => {
          return sum + (l.profit || 0);
        }, 0);

        setStats({
          activeListings: activeListings.length,
          totalRevenue,
          totalProfit,
          outOfStock: outOfStock.length,
        });
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const statItems = [
    {
      title: "出品中商品数",
      value: loading ? "..." : stats.activeListings.toString(),
      icon: Package,
      description: "アクティブな商品",
      color: "text-primary",
    },
    {
      title: "今月の売上",
      value: loading ? "..." : `¥${stats.totalRevenue.toLocaleString('ja-JP')}`,
      icon: DollarSign,
      description: "今月の総売上",
      color: "text-success",
    },
    {
      title: "利益額",
      value: loading ? "..." : `¥${stats.totalProfit.toLocaleString('ja-JP')}`,
      icon: TrendingUp,
      description: "今月の純利益",
      color: "text-info",
    },
    {
      title: "在庫切れ",
      value: loading ? "..." : stats.outOfStock.toString(),
      icon: AlertTriangle,
      description: "要確認商品",
      color: "text-warning",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">ダッシュボード</h1>
        <p className="text-muted-foreground mt-1">
          Amazon無在庫輸入ビジネスの概要を確認できます
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statItems.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>最近のアクティビティ</CardTitle>
            <CardDescription>直近の重要な更新</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-muted">
                <Package className="h-5 w-5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="text-sm font-medium">システムが起動しました</p>
                  <p className="text-xs text-muted-foreground">商品の監視を開始できます</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>クイックアクション</CardTitle>
            <CardDescription>よく使う機能へのショートカット</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <button 
                onClick={() => navigate('/research')}
                className="w-full p-3 text-left rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <div className="font-medium">商品をリサーチ</div>
                <div className="text-xs opacity-90">利益商品を検索</div>
              </button>
              <button 
                onClick={() => navigate('/products')}
                className="w-full p-3 text-left rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
              >
                <div className="font-medium">商品を一括登録</div>
                <div className="text-xs opacity-90">CSVから商品をインポート</div>
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

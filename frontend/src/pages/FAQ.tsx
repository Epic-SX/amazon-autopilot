import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { HelpCircle, Package, DollarSign, AlertCircle, CheckCircle2, Clock } from "lucide-react";

export default function FAQ() {
  const inventoryQuestions = [
    {
      id: "inventory-price-profit",
      question: "在庫機能に価格機能も含まれており利益が取れなくなった際に停止されますか？また、在庫機能には在庫が無くなった際に停止のみで再度販売された時の再出品機能は無い認識で合ってますか？",
      answer: "現在のバージョンでは、在庫機能は在庫が無くなった際の自動停止のみをサポートしています。利益が取れなくなった際の自動停止機能および在庫が復活した際の自動再出品機能は、現在は含まれていません。",
      status: "planned",
      phase: "第二フェーズまたは完成フェーズで追加予定",
    },
    {
      id: "inventory-price-fluctuation",
      question: "在庫機能に価格変動の自動反映は含まれてますか？",
      answer: "現在のバージョンでは、在庫機能に価格変動の自動反映機能は含まれていません。価格変動の自動反映機能は、第二フェーズまたは完成フェーズで追加を検討しています。",
      status: "planned",
      phase: "第二フェーズまたは完成フェーズで追加予定",
    },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "available":
        return <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" />利用可能</Badge>;
      case "planned":
        return <Badge className="bg-blue-500"><Clock className="h-3 w-3 mr-1" />予定</Badge>;
      case "not-available":
        return <Badge variant="secondary"><AlertCircle className="h-3 w-3 mr-1" />未対応</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
          <HelpCircle className="h-8 w-8 text-primary" />
          よくある質問（FAQ）
        </h1>
        <p className="text-muted-foreground mt-1">
          在庫機能に関するよくある質問と回答
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5 text-primary" />
            在庫機能について
          </CardTitle>
          <CardDescription>
            在庫管理機能に関する質問と回答
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible className="w-full">
            {inventoryQuestions.map((item) => (
              <AccordionItem key={item.id} value={item.id}>
                <AccordionTrigger className="text-left">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusBadge(item.status)}
                      </div>
                      <p className="font-medium">{item.question}</p>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 pt-2">
                    <p className="text-muted-foreground">{item.answer}</p>
                    {item.phase && (
                      <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                        <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                        <p className="text-sm text-blue-900 dark:text-blue-100">
                          <strong>追加予定:</strong> {item.phase}
                        </p>
                      </div>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-primary" />
            現在の在庫機能の機能一覧
          </CardTitle>
          <CardDescription>
            現在実装されている在庫機能
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-lg border bg-green-50 dark:bg-green-950">
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              <div>
                <p className="font-medium">在庫切れ時の自動停止</p>
                <p className="text-sm text-muted-foreground">
                  在庫が無くなった際に自動的に出品を停止します
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg border bg-blue-50 dark:bg-blue-950">
              <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <div>
                <p className="font-medium">利益が取れなくなった際の自動停止</p>
                <p className="text-sm text-muted-foreground">
                  第二フェーズまたは完成フェーズで追加予定
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg border bg-blue-50 dark:bg-blue-950">
              <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <div>
                <p className="font-medium">在庫復活時の自動再出品</p>
                <p className="text-sm text-muted-foreground">
                  第二フェーズまたは完成フェーズで追加予定
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg border bg-blue-50 dark:bg-blue-950">
              <Clock className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <div>
                <p className="font-medium">価格変動の自動反映</p>
                <p className="text-sm text-muted-foreground">
                  第二フェーズまたは完成フェーズで追加予定
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>お問い合わせ</CardTitle>
          <CardDescription>
            その他のご質問やご要望がございましたら、お気軽にお問い合わせください
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            機能追加のご要望やバグ報告など、お気軽にご連絡ください。
            開発チームが検討し、可能な限り対応いたします。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}



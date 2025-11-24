import { LayoutDashboard, Package, Search, Activity, Shield, Settings, HelpCircle } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

const menuItems = [
  { title: "ダッシュボード", url: "/", icon: LayoutDashboard },
  { title: "商品管理", url: "/products", icon: Package },
  { title: "リサーチ", url: "/research", icon: Search },
  { title: "監視設定", url: "/monitoring", icon: Activity },
  { title: "ブラックリスト", url: "/blacklist", icon: Shield },
  { title: "設定", url: "/settings", icon: Settings },
  { title: "よくある質問", url: "/faq", icon: HelpCircle },
];

export function AppSidebar() {
  const { open } = useSidebar();

  return (
    <Sidebar collapsible="icon">
      <SidebarContent>
        <div className="p-4 flex items-center gap-2 border-b border-sidebar-border">
          <Package className="h-6 w-6 text-primary" />
          {open && <span className="font-bold text-lg">Amazon Tool</span>}
        </div>
        
        <SidebarGroup>
          <SidebarGroupLabel>メニュー</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end={item.url === "/"}
                      className="flex items-center gap-3"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}

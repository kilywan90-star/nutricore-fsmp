import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "差序 - 商务出行AI智能助手",
  description: "出差有秩序，商务不焦虑。中国商务社交接待AI引擎——帮您搞定请客户吃饭、陪客户娱乐、送客户礼品全流程。",
  openGraph: {
    title: "差序 - 商务社交接待AI引擎",
    description: "帮商务人士搞定请客户吃饭→陪客户娱乐→送客户礼品全流程",
    type: "website",
    locale: "zh_CN",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

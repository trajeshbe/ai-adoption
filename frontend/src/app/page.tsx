import Link from "next/link";
import { Bot, MessageSquare, FileText, DollarSign } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";

const summaryCards = [
  {
    title: "Total Agents",
    value: "—",
    description: "Configured AI agents",
    icon: Bot,
    href: "/agents",
  },
  {
    title: "Active Sessions",
    value: "—",
    description: "Ongoing chat sessions",
    icon: MessageSquare,
    href: "/chat",
  },
  {
    title: "Documents Uploaded",
    value: "—",
    description: "Files in knowledge base",
    icon: FileText,
    href: "/documents",
  },
  {
    title: "Total Cost",
    value: "—",
    description: "Inference spend this period",
    icon: DollarSign,
    href: "/costs",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Overview of your AI Agent Platform.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {summaryCards.map((card) => {
          const Icon = card.icon;
          return (
            <Link key={card.title} href={card.href}>
              <Card className="hover:border-primary/40 transition-colors">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {card.title}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{card.value}</div>
                  <CardDescription>{card.description}</CardDescription>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Link href="/workflows">
          <Card className="hover:border-primary/40 transition-colors">
            <CardHeader>
              <CardTitle className="text-lg">Workflows</CardTitle>
              <CardDescription>
                View and manage agent DAG workflows.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/observability">
          <Card className="hover:border-primary/40 transition-colors">
            <CardHeader>
              <CardTitle className="text-lg">Observability</CardTitle>
              <CardDescription>
                Traces, logs, and metrics dashboards.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/agents/new">
          <Card className="hover:border-primary/40 transition-colors">
            <CardHeader>
              <CardTitle className="text-lg">Create Agent</CardTitle>
              <CardDescription>
                Set up a new AI agent with custom instructions.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}

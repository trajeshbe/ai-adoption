"use client";

import { GitBranch } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { DagViewer } from "@/components/workflows/DagViewer";

export default function WorkflowsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <GitBranch className="h-6 w-6" />
          <h1 className="text-3xl font-bold tracking-tight">Workflows</h1>
        </div>
        <p className="text-muted-foreground mt-1">
          Visualize agent DAG workflows and execution pipelines.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">DAG Viewer</CardTitle>
          <CardDescription>
            Interactive visualization of agent orchestration graphs.
          </CardDescription>
        </CardHeader>
        <CardContent className="min-h-[400px]">
          <DagViewer />
        </CardContent>
      </Card>
    </div>
  );
}

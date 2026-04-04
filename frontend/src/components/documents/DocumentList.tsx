"use client";

import { FileText, Trash2, Loader2, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useDocuments } from "@/lib/hooks/useDocuments";
import type { Document } from "@/types";

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function contentTypeBadgeVariant(
  contentType: string
): "default" | "secondary" | "outline" {
  if (contentType.includes("pdf")) return "default";
  if (contentType.includes("markdown") || contentType.includes("md"))
    return "secondary";
  return "outline";
}

function DocumentRow({
  doc,
  onDelete,
}: {
  doc: Document;
  onDelete?: (id: string) => void;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-4 rounded-md border p-4 transition-colors hover:bg-muted/50"
      )}
    >
      <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />

      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium">{doc.filename}</p>
        <p className="text-xs text-muted-foreground">
          {formatDate(doc.createdAt)}
        </p>
      </div>

      <Badge variant={contentTypeBadgeVariant(doc.contentType)}>
        {doc.contentType.split("/").pop() ?? doc.contentType}
      </Badge>

      <span className="shrink-0 text-xs text-muted-foreground">
        {doc.chunkCount} chunk{doc.chunkCount !== 1 ? "s" : ""}
      </span>

      {onDelete && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive"
          onClick={() => onDelete(doc.id)}
          aria-label={`Delete ${doc.filename}`}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

export function DocumentList() {
  const { documents, loading, deleteDocument } = useDocuments();

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">
            Loading documents...
          </span>
        </CardContent>
      </Card>
    );
  }

  if (!documents || documents.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-2 py-12">
          <Inbox className="h-10 w-10 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No documents uploaded yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          Documents ({documents.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {documents.map((doc) => (
          <DocumentRow
            key={doc.id}
            doc={doc}
            onDelete={deleteDocument}
          />
        ))}
      </CardContent>
    </Card>
  );
}

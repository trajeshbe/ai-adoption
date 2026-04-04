"use client";

import { FileText } from "lucide-react";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { DocumentList } from "@/components/documents/DocumentList";

export default function DocumentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <FileText className="h-6 w-6" />
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
        </div>
        <p className="text-muted-foreground mt-1">
          Upload and manage knowledge base documents.
        </p>
      </div>

      <UploadDropzone />
      <DocumentList />
    </div>
  );
}

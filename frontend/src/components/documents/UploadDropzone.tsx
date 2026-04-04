"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, FileText, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useDocuments } from "@/lib/hooks/useDocuments";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "text/markdown",
];

const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md"];

type UploadStatus = "idle" | "uploading" | "success" | "error";

export function UploadDropzone() {
  const { uploadDocument } = useDocuments();
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [fileName, setFileName] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isValidFile = (file: File): boolean => {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    return ACCEPTED_TYPES.includes(file.type) || ACCEPTED_EXTENSIONS.includes(ext);
  };

  const handleUpload = useCallback(
    async (file: File) => {
      if (!isValidFile(file)) {
        setStatus("error");
        setErrorMessage("Invalid file type. Please upload PDF, TXT, or MD files.");
        return;
      }

      setFileName(file.name);
      setStatus("uploading");
      setErrorMessage(null);

      try {
        await uploadDocument(file);
        setStatus("success");
        setTimeout(() => setStatus("idle"), 3000);
      } catch (err) {
        setStatus("error");
        setErrorMessage(
          err instanceof Error ? err.message : "Upload failed. Please try again."
        );
      }
    },
    [uploadDocument]
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload]
  );

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const onFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleUpload(file);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [handleUpload]
  );

  return (
    <Card>
      <CardContent className="p-6">
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          className={cn(
            "flex flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed p-10 transition-colors",
            dragOver
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-muted-foreground/50",
            status === "error" && "border-destructive/50 bg-destructive/5"
          )}
        >
          {status === "uploading" && (
            <>
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Uploading {fileName}...
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle className="h-10 w-10 text-green-500" />
              <p className="text-sm text-green-600">
                {fileName} uploaded successfully!
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <AlertCircle className="h-10 w-10 text-destructive" />
              <p className="text-sm text-destructive">{errorMessage}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStatus("idle")}
              >
                Try again
              </Button>
            </>
          )}

          {status === "idle" && (
            <>
              {dragOver ? (
                <FileText className="h-10 w-10 text-primary" />
              ) : (
                <Upload className="h-10 w-10 text-muted-foreground" />
              )}
              <div className="text-center">
                <p className="text-sm font-medium">
                  Drag and drop your file here
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Supports PDF, TXT, and MD files
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
              >
                Browse Files
              </Button>
            </>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS.join(",")}
            onChange={onFileSelect}
            className="hidden"
          />
        </div>
      </CardContent>
    </Card>
  );
}

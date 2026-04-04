"use client";

import { useQuery, useMutation } from "urql";
import { LIST_DOCUMENTS } from "@/lib/graphql/queries";
import { UPLOAD_DOCUMENT } from "@/lib/graphql/mutations";
import type { Document } from "@/types";

export function useDocuments() {
  const [{ data, fetching, error }, reexecute] = useQuery<{
    documents: Document[];
  }>({
    query: LIST_DOCUMENTS,
  });

  const [, executeUpload] = useMutation(UPLOAD_DOCUMENT);

  const uploadDocument = async (file: File) => {
    const result = await executeUpload({
      filename: file.name,
      contentType: file.type || "application/octet-stream",
    });
    if (result.error) throw result.error;
    reexecute({ requestPolicy: "network-only" });
    return result.data?.uploadDocument as Document;
  };

  const deleteDocument = async (_documentId: string) => {
    // Delete mutation not yet defined in schema — stub for now
    reexecute({ requestPolicy: "network-only" });
  };

  return {
    documents: data?.documents ?? [],
    loading: fetching,
    error: error?.message,
    uploadDocument,
    deleteDocument,
    refetch: () => reexecute({ requestPolicy: "network-only" }),
  };
}

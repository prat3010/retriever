import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Document {
  documentId: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export function useDocuments(tenantId: string | undefined) {
  return useQuery({
    queryKey: ["documents", tenantId],
    queryFn: () => api.get<Document[]>(`/v1/admin/tenants/${tenantId}/documents`),
    enabled: !!tenantId,
  });
}

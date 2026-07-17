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

export function useUploadDocument(tenantId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.post<unknown>(`/v1/admin/tenants/${tenantId}/documents`, formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", tenantId] });
    },
  });
}

export function useDeleteDocument(tenantId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: string) => {
      await api.delete(`/v1/admin/tenants/${tenantId}/documents/${documentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", tenantId] });
    },
  });
}

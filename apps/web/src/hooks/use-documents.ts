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

      const key = (await import("@/store/auth")).useAuthStore.getState().adminKey;
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const res = await fetch(`${API_BASE}/v1/admin/tenants/${tenantId}/documents`, {
        method: "POST",
        headers: {
          "X-Admin-Master-Key": key || "",
        },
        body: formData,
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || "Upload failed");
      }

      return res.json();
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

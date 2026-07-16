"use client";

import { useDocuments, useUploadDocument, useDeleteDocument } from "@/hooks/use-documents";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { FileText, UploadCloud, Trash2, Loader2 } from "lucide-react";
import { useState, useRef, DragEvent } from "react";
import { toast } from "sonner";

const statusVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  INDEXED: "default",
  PENDING: "secondary",
  PARSING: "outline",
  INDEXING: "outline",
  FAILED: "destructive",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function TenantDocumentsTab({ tenantId }: { tenantId: string }) {
  const { data: docs, isLoading, refetch } = useDocuments(tenantId);
  const uploadMutation = useUploadDocument(tenantId);
  const deleteMutation = useDeleteDocument(tenantId);

  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleUploadFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await handleUploadFiles(Array.from(e.target.files));
    }
  };

  const handleUploadFiles = async (files: File[]) => {
    const uploadToastId = toast.loading(`Uploading ${files.length} document(s)...`);
    
    try {
      let succeeded = 0;
      let failed = 0;

      for (const file of files) {
        try {
          await uploadMutation.mutateAsync(file);
          succeeded++;
        } catch (err: any) {
          console.error(err);
          failed++;
        }
      }

      if (failed === 0) {
        toast.success(`Successfully uploaded and queued ${succeeded} file(s) for indexing.`, {
          id: uploadToastId,
        });
      } else if (succeeded > 0) {
        toast.warning(`Uploaded ${succeeded} file(s), but ${failed} failed.`, {
          id: uploadToastId,
        });
      } else {
        toast.error("Failed to upload document(s). Check server configurations.", {
          id: uploadToastId,
        });
      }

      refetch();
    } catch (err) {
      toast.error("An unexpected error occurred during upload.", {
        id: uploadToastId,
      });
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This will drop all parsed chunks and vector records.`)) {
      return;
    }

    const deleteToastId = toast.loading(`Deleting ${filename}...`);
    try {
      await deleteMutation.mutateAsync(docId);
      toast.success(`Successfully deleted "${filename}".`, {
        id: deleteToastId,
      });
      refetch();
    } catch (err: any) {
      console.error(err);
      toast.error(`Failed to delete document: ${err.message || "Unknown error"}`, {
        id: deleteToastId,
      });
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  const isUploading = uploadMutation.isPending;

  return (
    <div className="space-y-6">
      {/* Premium Drag and Drop Upload Area */}
      <div
        className={`relative flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-lg transition-all duration-200 cursor-pointer ${
          isDragActive
            ? "border-primary bg-primary/5 scale-[0.99]"
            : "border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/10"
        } ${isUploading ? "opacity-60 pointer-events-none" : ""}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={triggerFileSelect}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          onChange={handleFileInputChange}
          accept=".pdf,.txt,.md,.markdown,.csv,.docx,.html"
        />

        {isUploading ? (
          <>
            <Loader2 className="h-10 w-10 mb-3 text-primary animate-spin" />
            <p className="text-sm font-medium">Processing uploads...</p>
            <p className="text-xs text-muted-foreground mt-1">Files are being securely parsed and sent to the indexing workers.</p>
          </>
        ) : (
          <>
            <UploadCloud className="h-10 w-10 mb-3 text-muted-foreground transition-colors group-hover:text-primary" />
            <p className="text-sm font-medium">
              <span className="text-primary underline">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-muted-foreground mt-1">PDF, TXT, MD, Markdown, CSV, DOCX (Max 20MB per file)</p>
          </>
        )}
      </div>

      {/* Documents Table */}
      <div className="border rounded-md overflow-hidden bg-card">
        {!docs || docs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <FileText className="h-12 w-12 mb-4" />
            <p className="text-sm">No documents uploaded yet</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Filename</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead className="w-[80px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {docs.map((doc) => (
                <TableRow key={doc.documentId}>
                  <TableCell className="font-medium max-w-[250px] truncate" title={doc.filename}>
                    {doc.filename}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatBytes(doc.fileSize)}</TableCell>
                  <TableCell className="text-muted-foreground text-xs">{doc.mimeType}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[doc.status] ?? "secondary"}>{doc.status}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(doc.createdAt).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(doc.documentId, doc.filename);
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}

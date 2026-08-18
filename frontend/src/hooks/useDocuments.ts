// 文档管理 hook：上传、列表、删除

import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { DocumentItem } from "../api/types";

export interface DocumentController {
  documents: DocumentItem[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  upload: (file: File) => Promise<{ ok: boolean; message: string }>;
  remove: (docId: string) => Promise<void>;
}

export function useDocuments(): DocumentController {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.listDocuments();
      setDocuments(resp.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const upload = useCallback(
    async (file: File) => {
      setUploading(true);
      setError(null);
      try {
        const resp = await api.upload(file);
        if (!resp.ok) {
          const msg = resp.error || "上传失败";
          setError(msg);
          return { ok: false, message: msg };
        }
        await refresh();
        return {
          ok: true,
          message: `已入库 ${resp.chunks_added ?? 0} 个片段（${resp.status || ""}）`,
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : "上传失败";
        setError(msg);
        return { ok: false, message: msg };
      } finally {
        setUploading(false);
      }
    },
    [refresh],
  );

  const remove = useCallback(
    async (docId: string) => {
      try {
        await api.deleteDocument(docId);
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "删除失败");
      }
    },
    [refresh],
  );

  return { documents, loading, uploading, error, refresh, upload, remove };
}

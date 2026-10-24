"use client";

import { useState } from "react";
import {
  useChatSessions,
  useChatSessionMessages,
  type ChatSessionSummary,
} from "@/hooks/use-chat-sessions";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  MessageSquare,
  Clock,
  User,
  Bot,
  Search,
  RefreshCw,
  Hash,
  ChevronRight,
  Terminal,
} from "lucide-react";

export function TenantChatHistoryTab({ tenantId }: { tenantId: string }) {
  const { data: sessions, isLoading, refetch, isRefetching } = useChatSessions(tenantId);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [filterText, setFilterText] = useState("");

  const activeSession = selectedSessionId
    ? sessions?.find((s) => s.session_id === selectedSessionId) || null
    : sessions?.[0] || null;

  const activeSessionId = activeSession?.session_id || null;

  const { data: messages, isLoading: isMessagesLoading } = useChatSessionMessages(
    tenantId,
    activeSessionId
  );

  const filteredSessions = (sessions || []).filter((s) => {
    if (!filterText.trim()) return true;
    const q = filterText.toLowerCase();
    return (
      s.session_id.toLowerCase().includes(q) ||
      (s.first_message_snippet && s.first_message_snippet.toLowerCase().includes(q)) ||
      (s.last_message_snippet && s.last_message_snippet.toLowerCase().includes(q))
    );
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Skeleton className="h-[500px] w-full" />
        <Skeleton className="h-[500px] md:col-span-2 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Tenant Chat Sessions</h2>
          <p className="text-sm text-muted-foreground">
            Inspect live inference dialogue, user conversations, and generated blueprints in real time.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isRefetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Badge variant="secondary" className="px-3 py-1 text-xs">
            {sessions?.length || 0} Total Sessions
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
        {/* Left Column: Session List */}
        <Card className="lg:col-span-5 flex flex-col h-[650px]">
          <CardHeader className="p-4 border-b">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Filter by session ID or text..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                className="pl-9 h-9 text-xs"
              />
            </div>
          </CardHeader>
          <CardContent className="p-0 overflow-y-auto flex-1 divide-y">
            {filteredSessions.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground text-sm">
                <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-40" />
                No chat sessions found for this tenant.
              </div>
            ) : (
              filteredSessions.map((session: ChatSessionSummary) => {
                const isSelected =
                  (selectedSessionId || activeSessionId) === session.session_id;
                const dateStr = session.created_at
                  ? new Date(session.created_at).toLocaleString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "Recent";

                return (
                  <div
                    key={session.session_id}
                    onClick={() => setSelectedSessionId(session.session_id)}
                    className={`p-3.5 cursor-pointer transition-colors text-left ${
                      isSelected
                        ? "bg-primary/10 border-l-4 border-l-primary"
                        : "hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs font-semibold truncate max-w-[200px]">
                        {session.session_id.slice(0, 18)}...
                      </span>
                      <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {dateStr}
                      </span>
                    </div>

                    <p className="text-xs text-foreground/80 line-clamp-2 mb-2 italic">
                      &ldquo;{session.first_message_snippet || session.last_message_snippet || "Empty session"}&rdquo;
                    </p>

                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="text-[10px] gap-1 px-1.5 py-0 font-mono">
                        <Hash className="h-2.5 w-2.5" />
                        {session.message_count} msgs
                      </Badge>
                      <ChevronRight className="h-3 w-3 text-muted-foreground" />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Right Column: Message Thread Viewer */}
        <Card className="lg:col-span-7 flex flex-col h-[650px]">
          <CardHeader className="p-4 border-b flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <Terminal className="h-4 w-4 text-primary" />
                Session: {activeSessionId || "None Selected"}
              </CardTitle>
              <CardDescription className="text-xs">
                {activeSession?.created_at
                  ? `Started ${new Date(activeSession.created_at).toLocaleString()}`
                  : "Select a session from the left pane"}
              </CardDescription>
            </div>
            {activeSession && (
              <Badge variant="secondary" className="text-xs font-mono">
                {messages?.length || 0} Messages
              </Badge>
            )}
          </CardHeader>

          <CardContent className="p-4 overflow-y-auto flex-1 space-y-4">
            {!activeSessionId ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-sm">
                <MessageSquare className="h-10 w-10 mb-2 opacity-30" />
                Select a chat session to view the transcript.
              </div>
            ) : isMessagesLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-3/4" />
                <Skeleton className="h-20 w-4/5 ml-auto" />
                <Skeleton className="h-16 w-2/3" />
              </div>
            ) : !messages || messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-sm">
                No messages recorded in this session.
              </div>
            ) : (
              messages.map((msg, idx) => {
                const isUser = msg.role === "user";
                const isSystem = msg.role === "system";

                return (
                  <div
                    key={idx}
                    className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                  >
                    {!isUser && (
                      <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                    )}

                    <div
                      className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed ${
                        isUser
                          ? "bg-primary text-primary-foreground font-sans"
                          : isSystem
                          ? "bg-amber-500/10 border border-amber-500/20 text-foreground font-mono"
                          : "bg-muted text-foreground border"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4 mb-1 border-b border-white/10 pb-1">
                        <span className="font-semibold uppercase text-[10px] tracking-wider opacity-80">
                          {msg.role}
                        </span>
                        {msg.created_at && (
                          <span className="text-[10px] opacity-60">
                            {new Date(msg.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>
                        )}
                      </div>

                      <div className="whitespace-pre-wrap font-sans">
                        {msg.content}
                      </div>
                    </div>

                    {isUser && (
                      <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center shrink-0 mt-0.5 text-primary-foreground">
                        <User className="h-4 w-4" />
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pause, Play, Trash2 } from "lucide-react";

interface LogEntry { timestamp?: string; level?: string; message?: string; type?: string; [key: string]: unknown; }

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/v1/logs/stream", { withCredentials: true });
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (event) => {
      if (paused) return;
      try {
        const data = JSON.parse(event.data);
        setLogs((prev) => [...prev.slice(-500), data]);
      } catch {
        setLogs((prev) => [...prev.slice(-500), { message: event.data }]);
      }
    };

    return () => es.close();
  }, [paused]);

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, paused]);

  const levelColor = (level?: string) => {
    switch (level?.toUpperCase()) {
      case "ERROR": case "CRITICAL": return "danger";
      case "WARNING": return "warning";
      case "INFO": return "success";
      default: return "secondary";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Live Logs</h1>
        <div className="flex items-center gap-2">
          <Badge variant={connected ? "success" : "danger"}>
            {connected ? "Connected" : "Disconnected"}
          </Badge>
          <Button size="sm" variant="outline" onClick={() => setPaused(!paused)}>
            {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          </Button>
          <Button size="sm" variant="outline" onClick={() => setLogs([])}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">{logs.length} entries {paused && "(paused)"}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-[70vh] overflow-y-auto rounded-lg bg-muted p-3 font-mono text-xs space-y-1">
            {logs.length === 0 && <p className="text-muted-foreground">Waiting for log entries...</p>}
            {logs.map((log, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-muted-foreground whitespace-nowrap">
                  {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "—"}
                </span>
                {log.level && <Badge variant={levelColor(log.level)} className="text-[10px] px-1">{log.level}</Badge>}
                <span className="break-all">{log.message || JSON.stringify(log)}</span>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

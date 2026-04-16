import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Box, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { listContainers, restartContainer } from "@/api/docker";

interface Container { name: string; cpu: string; memory: string; network: string; pids: string; }

export default function DockerPage() {
  const queryClient = useQueryClient();

  const { data: containers, isLoading, isError } = useQuery({
    queryKey: ["docker-containers"],
    queryFn: () => listContainers().then((r) => r.data as Container[]),
    refetchInterval: 15_000,
  });

  const restartMut = useMutation({
    mutationFn: (name: string) => restartContainer(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["docker-containers"] }),
  });

  if (isLoading) return <LoadingSpinner text="Loading containers..." />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Docker Monitoring</h1>

      {isError && (
        <Card><CardContent className="p-6 text-center text-muted-foreground">
          Docker API not available. Make sure the Docker socket is accessible.
        </CardContent></Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {containers?.map((c: Container) => (
          <Card key={c.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Box className="h-4 w-4" />{c.name}
              </CardTitle>
              <Badge variant="success">Running</Badge>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-muted-foreground">CPU:</span> {c.cpu}</div>
                <div><span className="text-muted-foreground">Memory:</span> {c.memory}</div>
                <div><span className="text-muted-foreground">Network:</span> {c.network}</div>
                <div><span className="text-muted-foreground">PIDs:</span> {c.pids}</div>
              </div>
              <Button
                size="sm" variant="outline" className="mt-3"
                onClick={() => { if (confirm(`Restart ${c.name}?`)) restartMut.mutate(c.name); }}
                disabled={restartMut.isPending}
              >
                <RefreshCw className="mr-1 h-3 w-3" />Restart
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

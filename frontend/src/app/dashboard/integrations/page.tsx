"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardHeader, CardTitle } from "@/components/Card";
import { StatusBadge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Input, Label } from "@/components/Input";
import { Skeleton } from "@/components/Skeleton";
import { useToast } from "@/components/Toast";
import { api, ApiError, type IntegrationsResponse, type IntegrationStatus } from "@/lib/api";

function OtterReturnBanner() {
  const params = useSearchParams();
  const otter = params.get("otter");
  if (!otter) return null;
  if (otter === "connected") {
    return (
      <div className="rounded-lg border border-success/30 bg-success-soft px-4 py-3 text-sm text-success">
        Otter AI connected successfully.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
      Connecting Otter AI failed. Please try again.
    </div>
  );
}

function DiscordCard({ status, onConnected }: { status: IntegrationStatus; onConnected: () => void }) {
  const [botToken, setBotToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const toast = useToast();

  async function connect() {
    setError(null);
    setPending(true);
    try {
      await api.put("/integrations/discord", { bot_token: botToken });
      setBotToken("");
      onConnected();
      toast.show("Discord connected.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setPending(false);
    }
  }

  async function disconnect() {
    setPending(true);
    try {
      await api.del("/integrations/discord");
      onConnected();
      toast.show("Discord disconnected.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Discord</CardTitle>
        <StatusBadge status={status.status} />
      </CardHeader>
      {status.status === "connected" ? (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted">Bot token {status.masked_hint}</p>
          <Button variant="secondary" onClick={disconnect} disabled={pending}>
            Disconnect
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <Label htmlFor="discord-token">Bot token</Label>
            <Input
              id="discord-token"
              type="password"
              value={botToken}
              onChange={(e) => setBotToken(e.target.value)}
              placeholder="Discord bot token"
            />
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button onClick={connect} disabled={pending || !botToken}>
            {pending ? "Connecting..." : "Connect"}
          </Button>
        </div>
      )}
    </Card>
  );
}

function TrelloCard({ status, onConnected }: { status: IntegrationStatus; onConnected: () => void }) {
  const [apiKey, setApiKey] = useState("");
  const [token, setToken] = useState("");
  const [boardId, setBoardId] = useState("");
  const [listId, setListId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const toast = useToast();

  async function connect() {
    setError(null);
    setPending(true);
    try {
      await api.put("/integrations/trello", { api_key: apiKey, token, board_id: boardId, list_id: listId });
      onConnected();
      toast.show("Trello connected.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setPending(false);
    }
  }

  async function disconnect() {
    setPending(true);
    try {
      await api.del("/integrations/trello");
      onConnected();
      toast.show("Trello disconnected.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trello</CardTitle>
        <StatusBadge status={status.status} />
      </CardHeader>
      {status.status === "connected" ? (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted">Token {status.masked_hint}</p>
          <Button variant="secondary" onClick={disconnect} disabled={pending}>
            Disconnect
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="trello-key">API key</Label>
              <Input id="trello-key" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="trello-token">Token</Label>
              <Input
                id="trello-token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="trello-board">Board ID</Label>
              <Input id="trello-board" value={boardId} onChange={(e) => setBoardId(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="trello-list">List ID</Label>
              <Input id="trello-list" value={listId} onChange={(e) => setListId(e.target.value)} />
            </div>
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button onClick={connect} disabled={pending || !apiKey || !token || !boardId || !listId}>
            {pending ? "Connecting..." : "Connect"}
          </Button>
        </div>
      )}
    </Card>
  );
}

function GeminiCard({ status, onConnected }: { status: IntegrationStatus; onConnected: () => void }) {
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const toast = useToast();

  async function connect() {
    setError(null);
    setPending(true);
    try {
      await api.put("/integrations/gemini", { api_key: apiKey });
      setApiKey("");
      onConnected();
      toast.show("Gemini key connected.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setPending(false);
    }
  }

  async function disconnect() {
    setPending(true);
    try {
      await api.del("/integrations/gemini");
      onConnected();
      toast.show("Gemini key disconnected.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Gemini / OpenAI model key</CardTitle>
        <StatusBadge status={status.status} />
      </CardHeader>
      {status.status === "connected" ? (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted">Key {status.masked_hint}</p>
          <Button variant="secondary" onClick={disconnect} disabled={pending}>
            Disconnect
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <Label htmlFor="gemini-key">API key</Label>
            <Input
              id="gemini-key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button onClick={connect} disabled={pending || !apiKey}>
            {pending ? "Connecting..." : "Connect"}
          </Button>
        </div>
      )}
    </Card>
  );
}

function OtterCard({ status, onConnected }: { status: IntegrationStatus; onConnected: () => void }) {
  const [pending, setPending] = useState(false);
  const toast = useToast();

  async function disconnect() {
    setPending(true);
    try {
      await api.del("/integrations/otter");
      onConnected();
      toast.show("Otter AI disconnected.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Otter AI</CardTitle>
        <StatusBadge status={status.status} />
      </CardHeader>
      {status.status === "connected" ? (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted">{status.masked_hint}</p>
          <Button variant="secondary" onClick={disconnect} disabled={pending}>
            Disconnect
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-muted">Authorize access to your Otter AI meetings.</p>
          <a href="/api/v1/integrations/otter/authorize">
            <Button>Connect Otter AI</Button>
          </a>
        </div>
      )}
    </Card>
  );
}

function IntegrationsGrid() {
  const [data, setData] = useState<IntegrationsResponse | null>(null);

  async function refresh() {
    const res = await api.get<IntegrationsResponse>("/integrations");
    setData(res);
  }

  useEffect(() => {
    // Client-side fetch-on-mount is intentional: this page's data changes on
    // every connect/disconnect action within the same session (see
    // `onConnected={refresh}` below), so it isn't a one-shot server load.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, []);

  if (!data) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <DiscordCard status={data.discord} onConnected={refresh} />
      <OtterCard status={data.otter} onConnected={refresh} />
      <TrelloCard status={data.trello} onConnected={refresh} />
      <GeminiCard status={data.gemini} onConnected={refresh} />
    </div>
  );
}

export default function IntegrationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Integrations</h1>
        <p className="mt-1 text-sm text-muted">
          Connect your own Discord bot, Otter AI account, Trello board, and AI model key.
          Nothing here is shared with any other account.
        </p>
      </div>
      <Suspense fallback={null}>
        <OtterReturnBanner />
      </Suspense>
      <IntegrationsGrid />
    </div>
  );
}

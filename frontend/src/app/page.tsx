import Link from "next/link";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

const FEATURES = [
  {
    title: "Structured meeting summaries",
    description:
      "Every transcript becomes an overview, key decisions, risks, open questions, and follow-ups — never invented, never guessed.",
  },
  {
    title: "Action items with owners",
    description:
      "Each action item ships with a task description, owner, deadline, priority, and confidence score, extracted automatically.",
  },
  {
    title: "Automatic Trello tasks",
    description:
      "Validated action items become tracked Trello cards, assigned by your own configurable rules — no duplicates, nothing forgotten.",
  },
  {
    title: "Daily executive reports",
    description:
      "A morning briefing and an evening wrap-up, covering meetings, deadlines, and priorities, delivered on your schedule.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <span className="text-sm font-semibold tracking-tight">MeetMind</span>
          <nav className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-muted hover:text-foreground">
              Log in
            </Link>
            <Link href="/signup">
              <Button>Sign up</Button>
            </Link>
          </nav>
        </div>
      </header>

      <section className="relative flex flex-col items-center overflow-hidden px-6 py-24 text-center">
        <div aria-hidden="true" className="hero-background">
          <div className="hero-blob hero-blob-1" />
          <div className="hero-blob hero-blob-2" />
          <div className="hero-blob hero-blob-3" />
        </div>

        <div className="relative z-10 mx-auto flex max-w-3xl flex-col items-center">
          <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-medium text-accent">
            AI Meeting Assistant
          </span>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
            Your meetings, turned into action — automatically.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-muted">
            Connect your own Otter AI, Discord, and Trello accounts. MeetMind retrieves your
            transcripts, writes the summary, tracks the action items, and keeps everyone
            reported — so nothing discussed in a meeting gets forgotten.
          </p>
          <div className="mt-8 flex items-center gap-3">
            <Link href="/signup">
              <Button className="px-6 py-3 text-base">Get started free</Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary" className="px-6 py-3 text-base">
                I already have an account
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 px-6 pb-24 sm:grid-cols-2">
        {FEATURES.map((feature) => (
          <Card key={feature.title}>
            <h3 className="text-base font-semibold text-foreground">{feature.title}</h3>
            <p className="mt-2 text-sm text-muted">{feature.description}</p>
          </Card>
        ))}
      </section>

      <footer className="border-t border-border py-8 text-center text-sm text-muted">
        Every user connects their own Discord, Otter AI, Trello, and AI model key — your
        workspace is yours alone.
      </footer>
    </div>
  );
}

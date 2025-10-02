export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm">
        <h1 className="mb-4 text-4xl font-bold">LICS - Lab Instrument Control System</h1>
        <p className="text-lg text-muted-foreground">
          Cloud-native platform for managing laboratory instruments and conducting behavioral
          experiments
        </p>
        <div className="mt-8 flex gap-4">
          <div className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
            <h3 className="mb-2 text-xl font-semibold">Frontend Initialized</h3>
            <p className="text-sm text-muted-foreground">
              Next.js 14 with TypeScript and Tailwind CSS
            </p>
          </div>
          <div className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
            <h3 className="mb-2 text-xl font-semibold">Ready for Development</h3>
            <p className="text-sm text-muted-foreground">
              Phase 3 Week 5 Day 1-2 Implementation in Progress
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}

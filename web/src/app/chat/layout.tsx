import { redirect } from "next/navigation";
import type { Route } from "next";
import { unstable_noStore as noStore } from "next/cache";
import { requireAuth } from "@/lib/auth/requireAuth";
import { ProjectsProvider } from "./projects/ProjectsContext";
import AppSidebar from "@/sections/sidebar/AppSidebar";

export interface LayoutProps {
  children: React.ReactNode;
}

export default async function Layout({ children }: LayoutProps) {
  noStore();

  // Only check authentication - data fetching is done client-side via SWR hooks
  const authResult = await requireAuth();

  if (authResult.redirect) {
    redirect(authResult.redirect as Route);
  }

  return (
    <ProjectsProvider>
      <div className="flex flex-row w-full h-full bg-background-tint-01 overflow-hidden">
        <AppSidebar />
        <main className="flex-1 h-full min-w-0 py-2 pr-2 flex flex-col">
          <div className="flex-1 rounded-2xl border border-border-02 shadow-lg bg-background overflow-hidden relative flex flex-col">
            {children}
          </div>
        </main>
      </div>
    </ProjectsProvider>
  );
}

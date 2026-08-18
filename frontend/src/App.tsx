import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppSidebar } from "@/components/AppSidebar";
import { lazy, Suspense } from "react";
import { CardSkeleton } from "@/components/LoadingSkeleton";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Fixtures = lazy(() => import("./pages/Fixtures"));
const Chat = lazy(() => import("./pages/Chat"));
const LiveMatch = lazy(() => import("./pages/LiveMatch"));
const News = lazy(() => import("./pages/News"));
const NotFound = lazy(() => import("./pages/NotFound"));

const queryClient = new QueryClient();

function PageLoader() {
  return (
    <div className="space-y-6 p-8">
      <CardSkeleton />
      <CardSkeleton />
    </div>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Sonner />
      <BrowserRouter>
        <div className="flex min-h-screen w-full">
          <AppSidebar />
          <main className="flex-1 max-w-[1200px] p-6 lg:p-8">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/fixtures" element={<Fixtures />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/live" element={<LiveMatch />} />
                <Route path="/news" element={<News />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

import { QueryClient, QueryClientProvider as RQProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
});

export function AppQueryClientProvider({ children }: { children: ReactNode }) {
  return <RQProvider client={queryClient}>{children}</RQProvider>;
}

export { queryClient };
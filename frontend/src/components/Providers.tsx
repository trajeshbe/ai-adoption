"use client";

import { Provider as UrqlProvider } from "urql";
import { client } from "@/lib/graphql/client";

export function Providers({ children }: { children: React.ReactNode }) {
  return <UrqlProvider value={client}>{children}</UrqlProvider>;
}

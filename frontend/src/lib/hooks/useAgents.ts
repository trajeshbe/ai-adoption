"use client";

import { useQuery, useMutation } from "urql";
import { LIST_AGENTS, GET_AGENT } from "@/lib/graphql/queries";
import { CREATE_AGENT, DELETE_AGENT } from "@/lib/graphql/mutations";
import type { Agent, AgentType } from "@/types";

export function useAgents() {
  const [{ data, fetching, error }, reexecute] = useQuery<{ agents: Agent[] }>({
    query: LIST_AGENTS,
  });

  const [, executeCreate] = useMutation(CREATE_AGENT);
  const [, executeDelete] = useMutation(DELETE_AGENT);

  const createAgent = async (input: {
    name: string;
    agentType: AgentType;
    instructions: string;
  }) => {
    const result = await executeCreate({ input });
    if (result.error) throw result.error;
    reexecute({ requestPolicy: "network-only" });
    return result.data?.createAgent as Agent;
  };

  const deleteAgent = async (agentId: string) => {
    const result = await executeDelete({ agentId });
    if (result.error) throw result.error;
    reexecute({ requestPolicy: "network-only" });
    return result.data?.deleteAgent;
  };

  return {
    agents: data?.agents ?? [],
    loading: fetching,
    error: error?.message,
    createAgent,
    deleteAgent,
    refetch: () => reexecute({ requestPolicy: "network-only" }),
  };
}

export function useAgent(agentId: string) {
  const [{ data, fetching, error }] = useQuery<{ agent: Agent }>({
    query: GET_AGENT,
    variables: { id: agentId },
    pause: !agentId,
  });

  return {
    agent: data?.agent,
    loading: fetching,
    error: error?.message,
  };
}

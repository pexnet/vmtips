import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { leaguesApi } from "../api/client";
import type { League, LeagueDetail } from "../types/api";

export function useLeagues() {
  return useQuery<League[]>({
    queryKey: ["leagues"],
    queryFn: async () => {
      const res = await leaguesApi.list();
      const data = res.data as League[] | { leagues?: League[] };
      // Backend returns League[] directly (not { leagues: [...] })
      if (Array.isArray(data)) return data;
      return (data as { leagues?: League[] }).leagues || [];
    },
  });
}

export function useLeagueDetail(id: number | null) {
  return useQuery<LeagueDetail>({
    queryKey: ["leagues", id],
    queryFn: async () => {
      if (!id) throw new Error("League ID is required");
      const res = await leaguesApi.detail(id);
      return res.data as LeagueDetail;
    },
    enabled: !!id,
  });
}

/** Invalidate leagues cache so a refetch is triggered after mutations (create/join). */
export function useInvalidateLeagues() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({ queryKey: ["leagues"] });
}


// ── League Bonus Questions ─────────────────────────────────────

export function useLeagueBonusQuestions(leagueId: number | null) {
  return useQuery({
    queryKey: ["leagues", leagueId, "bonus-questions"],
    queryFn: async () => {
      if (!leagueId) return [];
      const res = await leaguesApi.listBonusQuestions(leagueId);
      return res.data as Array<{
        id: number;
        league_id: number;
        question_text: string;
        points_value: number;
        answer: string | null;
        created_at: string | null;
      }>;
    },
    enabled: !!leagueId,
  });
}

export function useCreateBonusQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ leagueId, payload }: { leagueId: number; payload: { question_text: string; points_value: number; answer?: string } }) => {
      const res = await leaguesApi.createBonusQuestion(leagueId, payload);
      return res.data;
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["leagues", vars.leagueId, "bonus-questions"] });
    },
  });
}

export function useUpdateBonusQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ leagueId, questionId, payload }: { leagueId: number; questionId: number; payload: { question_text?: string; points_value?: number; answer?: string } }) => {
      const res = await leaguesApi.updateBonusQuestion(leagueId, questionId, payload);
      return res.data;
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["leagues", vars.leagueId, "bonus-questions"] });
    },
  });
}

export function useDeleteBonusQuestion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ leagueId, questionId }: { leagueId: number; questionId: number }) => {
      const res = await leaguesApi.deleteBonusQuestion(leagueId, questionId);
      return res.data;
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["leagues", vars.leagueId, "bonus-questions"] });
    },
  });
}

export function useMyBonusAnswer(leagueId: number | null, questionId: number | null) {
  return useQuery({
    queryKey: ["leagues", leagueId, "bonus-questions", questionId, "answer"],
    queryFn: async () => {
      if (!leagueId || !questionId) return null;
      const res = await leaguesApi.getMyBonusAnswer(leagueId, questionId);
      return res.data as {
        question_id: number;
        answer_text: string | null;
        is_correct: boolean | null;
        points_awarded: number | null;
      };
    },
    enabled: !!leagueId && !!questionId,
  });
}

export function useSaveBonusAnswer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ leagueId, questionId, answerText }: { leagueId: number; questionId: number; answerText: string }) => {
      const res = await leaguesApi.saveBonusAnswer(leagueId, questionId, answerText);
      return res.data;
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["leagues", vars.leagueId, "bonus-questions", vars.questionId, "answer"] });
      queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
    },
  });
}

export function usePublicLeagues() {
  return useQuery<League[]>({
    queryKey: ["leagues", "public"],
    queryFn: async () => {
      const res = await leaguesApi.public();
      return res.data as League[];
    },
  });
}

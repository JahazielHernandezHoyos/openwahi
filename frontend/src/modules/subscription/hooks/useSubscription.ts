import { useQuery } from "@tanstack/react-query";
import { getMySubscription } from "../service";

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription", "me"],
    queryFn: getMySubscription,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

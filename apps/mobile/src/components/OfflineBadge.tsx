import { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import NetInfo from "@react-native-community/netinfo";
import { peekPickQueue, removePickOp } from "@/lib/offlinePickQueue";
import { fetchWithAuth } from "@/api/client";
import { colors, radius, spacing } from "@/theme/tokens";
import type { PickResult } from "@/types/api";

interface Props {
  invite_code: string;
}

// Drains the AsyncStorage pick queue after reconnect. Fires when the device
// transitions from offline → online. Handles only the app-kill-while-offline
// case — React Query's onlineManager auto-retries in-memory paused mutations.
async function drainQueue(invite_code: string, onDone: () => void): Promise<void> {
  const ops = await peekPickQueue();
  if (ops.length === 0) { onDone(); return; }
  for (const op of ops) {
    try {
      if (op.is_picked) {
        await fetchWithAuth<PickResult>(`/api/groups/${op.invite_code}/picks/${op.set_id}`, {
          method: "DELETE",
          body: JSON.stringify({ state_clock_ms: Date.now() }),
        });
      } else {
        await fetchWithAuth<PickResult>(`/api/groups/${op.invite_code}/picks`, {
          method: "POST",
          body: JSON.stringify({ set_id: op.set_id, state: "active", state_clock_ms: Date.now() }),
        });
      }
      await removePickOp(op.invite_code, op.set_id);
    } catch {
      // Leave in queue — will retry on next reconnect
    }
  }
  onDone();
}

export function OfflineBadge({ invite_code }: Props) {
  const queryClient = useQueryClient();
  const [isOffline, setIsOffline] = useState(false);
  const [pausedCount, setPausedCount] = useState(0);
  const prevOnline = useRef<boolean | null>(null);
  const draining = useRef(false);

  // Track paused pick-toggle mutations from React Query's MutationCache
  useEffect(() => {
    const unsub = queryClient.getMutationCache().subscribe(() => {
      const count = queryClient
        .getMutationCache()
        .getAll()
        .filter(
          (m) =>
            Array.isArray(m.options.mutationKey) &&
            m.options.mutationKey[0] === "pick-toggle" &&
            m.state.isPaused,
        ).length;
      setPausedCount(count);
    });
    return unsub;
  }, [queryClient]);

  // Watch network state: update badge + drain queue on reconnect
  useEffect(() => {
    const unsub = NetInfo.addEventListener((state) => {
      const online = !!state.isConnected && state.isInternetReachable !== false;
      const wasOffline = prevOnline.current === false;
      prevOnline.current = online;
      setIsOffline(!online);

      if (wasOffline && online && !draining.current) {
        draining.current = true;
        void drainQueue(invite_code, () => {
          draining.current = false;
          void queryClient.invalidateQueries({ queryKey: ["group", invite_code] });
          void queryClient.invalidateQueries({ queryKey: ["group-schedule", invite_code] });
        });
      }
    });
    return unsub;
  }, [invite_code, queryClient]);

  if (!isOffline && pausedCount === 0) return null;

  const label =
    pausedCount > 0
      ? `${pausedCount} pick${pausedCount > 1 ? "s" : ""} pending sync`
      : "Offline — picks queued";

  return (
    <View style={styles.badge} testID="offline-badge">
      <View style={styles.dot} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "center",
    gap: spacing[2],
    backgroundColor: colors.bg.elevated,
    borderWidth: 1,
    borderColor: colors.border.mid,
    borderRadius: radius.full,
    paddingHorizontal: spacing[5],
    paddingVertical: 5,
    marginHorizontal: spacing.screenPad,
    marginBottom: spacing[3],
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: radius.full,
    backgroundColor: colors.neon.pink,
  },
  label: {
    fontFamily: "Manrope-SemiBold",
    fontSize: 12,
    color: colors.text.secondary,
  },
});

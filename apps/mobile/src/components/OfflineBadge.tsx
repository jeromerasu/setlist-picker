import { useEffect, useRef } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useIsMutating, useQueryClient } from "@tanstack/react-query";
import { useNetInfo } from "@react-native-community/netinfo";
import { peekPickQueue, removePickOp } from "@/lib/offlinePickQueue";
import { fetchWithAuth } from "@/api/client";
import { colors, radius, spacing } from "@/theme/tokens";
import type { PickResult } from "@/types/api";

interface Props {
  invite_code: string;
}

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
  const netInfo = useNetInfo();
  const pendingMutations = useIsMutating({ mutationKey: ["pick-toggle"] });
  const queryClient = useQueryClient();
  const prevOnline = useRef<boolean | null>(null);
  const draining = useRef(false);

  const isOffline = netInfo.isInternetReachable === false;

  // Drain AsyncStorage queue on reconnect (app-kill-while-offline recovery path).
  // React Query's onlineManager handles the in-memory paused-mutation resume;
  // this effect handles ops that were queued in a previous app session.
  useEffect(() => {
    const online = !isOffline;
    const wasOffline = prevOnline.current === false;
    prevOnline.current = online;

    if (wasOffline && online && !draining.current) {
      draining.current = true;
      void drainQueue(invite_code, () => {
        draining.current = false;
        void queryClient.invalidateQueries({ queryKey: ["group", invite_code] });
        void queryClient.invalidateQueries({ queryKey: ["group-schedule", invite_code] });
      });
    }
  }, [isOffline, invite_code, queryClient]);

  if (!isOffline && pendingMutations === 0) return null;

  const label = isOffline
    ? "Offline — picks queued"
    : `Syncing ${pendingMutations} pick${pendingMutations > 1 ? "s" : ""}…`;

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
    backgroundColor: colors.bg.surfaceMed,
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
    fontFamily: "Manrope-Medium",
    fontSize: 12,
    color: colors.text.iconAccent,
  },
});

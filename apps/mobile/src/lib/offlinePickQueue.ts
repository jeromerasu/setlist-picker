import AsyncStorage from "@react-native-async-storage/async-storage";

const QUEUE_KEY = "@picks_offline_queue_v1";

export interface QueuedPickOp {
  invite_code: string;
  set_id: string;
  is_picked: boolean;
  member_id: string;
  queued_at: number;
}

async function _read(): Promise<QueuedPickOp[]> {
  const raw = await AsyncStorage.getItem(QUEUE_KEY);
  if (!raw) return [];
  try { return JSON.parse(raw) as QueuedPickOp[]; } catch { return []; }
}

async function _write(ops: QueuedPickOp[]): Promise<void> {
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(ops));
}

// Upsert: keyed by (invite_code, set_id) — last tap wins
export async function enqueuePickOp(op: QueuedPickOp): Promise<void> {
  const ops = await _read();
  const filtered = ops.filter((o) => !(o.invite_code === op.invite_code && o.set_id === op.set_id));
  await _write([...filtered, op]);
}

// Remove a specific op (called on mutation success or permanent server error)
export async function removePickOp(invite_code: string, set_id: string): Promise<void> {
  const ops = await _read();
  await _write(ops.filter((o) => !(o.invite_code === invite_code && o.set_id === set_id)));
}

// Return all queued ops without clearing — use removePickOp per-item after successful replay
export async function peekPickQueue(): Promise<QueuedPickOp[]> {
  return _read();
}

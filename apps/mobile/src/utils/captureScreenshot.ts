import { Share } from "react-native";
import ViewShot, { type CaptureOptions } from "react-native-view-shot";

export async function captureAndShare(
  viewShotRef: React.RefObject<ViewShot>,
  filename: string
): Promise<void> {
  const opts: CaptureOptions = { format: "png", quality: 1 };
  const uri = await viewShotRef.current?.capture?.(opts);
  if (uri == null) return;
  await Share.share({ url: uri, title: filename });
}

import { Share } from "react-native";

export async function shareInvite(groupName: string, inviteCode: string): Promise<void> {
  await Share.share({
    message: `Join "${groupName}" on setlist-picker! Code: ${inviteCode}`,
  });
}

// Centralized navigation param types for all stacks.

export type HomeStackParamList = {
  GroupsList: undefined;
  GroupDetail: { invite_code: string };
  CreateGroup: { selectedEvent?: { event_id: string; name: string } };
  EventPicker: undefined;
  JoinGroup: undefined;
  Schedule: { invite_code: string };
  ArtistDetail: { artist_name: string };
  RightNowSnapshot: { invite_code: string; at?: string };
};

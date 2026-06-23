// Stub declaration for expo-av (not installed yet — audio preview is Wave 4+)
declare module "expo-av" {
  export namespace Audio {
    interface PlaybackStatus {
      isLoaded: boolean;
      didJustFinish?: boolean;
    }
    class Sound {
      static createAsync(source: { uri: string }): Promise<{ sound: Sound }>;
      playAsync(): Promise<void>;
      stopAsync(): Promise<void>;
      unloadAsync(): Promise<void>;
      setOnPlaybackStatusUpdate(callback: (status: PlaybackStatus) => void): void;
    }
  }
}

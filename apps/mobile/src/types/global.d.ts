// Stub for react-native-view-shot (not installed yet — screenshot share is Wave 4+)
declare module "react-native-view-shot" {
  import { Component } from "react";
  export interface CaptureOptions {
    format?: string;
    quality?: number;
  }
  export default class ViewShot extends Component<any> {
    capture(options?: CaptureOptions): Promise<string>;
  }
}

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

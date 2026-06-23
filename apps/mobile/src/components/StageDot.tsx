import { StyleSheet, View } from "react-native";

export interface StageDotProps {
  color: string;
  size?: 8 | 9 | 11;
  withGlow?: boolean;
}

export function StageDot({ color, size = 9, withGlow = false }: StageDotProps) {
  const haloSize = Math.round(size * 1.6);
  const haloOffset = Math.round((haloSize - size) / 2);

  return (
    <View style={[styles.wrapper, { width: haloSize, height: haloSize }]}>
      {withGlow && (
        <View
          style={[
            styles.halo,
            {
              width: haloSize,
              height: haloSize,
              borderRadius: haloSize / 2,
              backgroundColor: color,
              opacity: 0.3,
            },
          ]}
        />
      )}
      <View
        style={[
          styles.dot,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
            backgroundColor: color,
            top: withGlow ? haloOffset : 0,
            left: withGlow ? haloOffset : 0,
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: "relative",
    alignItems: "center",
    justifyContent: "center",
  },
  halo: {
    position: "absolute",
  },
  dot: {
    position: "absolute",
  },
});

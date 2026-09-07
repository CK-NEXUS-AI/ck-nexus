import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { DiditBusinessVerification } from "./DiditBusinessVerification";

export default function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(
    process.env.EXPO_PUBLIC_CKNEXUS_API_BASE_URL ?? "",
  );
  const [accessToken, setAccessToken] = useState("");

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.page}>
        <Text style={styles.heading}>CK-NEXUS KYB</Text>
        <Text style={styles.note}>
          Development client. Didit secrets stay on the CK-NEXUS backend.
        </Text>
        <View style={styles.field}>
          <Text style={styles.label}>CK-NEXUS API base URL</Text>
          <TextInput
            value={apiBaseUrl}
            onChangeText={setApiBaseUrl}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="https://your-ck-nexus-gateway.example"
            style={styles.input}
          />
        </View>
        <View style={styles.field}>
          <Text style={styles.label}>Your CK-NEXUS bearer token</Text>
          <TextInput
            value={accessToken}
            onChangeText={setAccessToken}
            autoCapitalize="none"
            autoCorrect={false}
            secureTextEntry
            placeholder="JWT from your app authentication"
            style={styles.input}
          />
          <Text style={styles.hint}>
            Stored only in this screen state; it is not written to source or logs.
          </Text>
        </View>
        <DiditBusinessVerification
          apiBaseUrl={apiBaseUrl}
          getAccessToken={async () => accessToken}
        />
        <StatusBar style="auto" />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  page: {
    alignItems: "center",
    gap: 18,
    padding: 24,
  },
  heading: { fontSize: 30, fontWeight: "800" },
  note: { fontSize: 14, lineHeight: 20, maxWidth: 560, width: "100%" },
  field: { gap: 8, maxWidth: 560, width: "100%" },
  label: { fontSize: 14, fontWeight: "600" },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  hint: { fontSize: 12, lineHeight: 17 },
});

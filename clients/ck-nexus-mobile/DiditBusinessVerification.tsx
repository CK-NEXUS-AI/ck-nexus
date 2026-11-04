import { useState } from "react";
import {
  ActivityIndicator,
  Button,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import * as Didit from "@didit-protocol/sdk-react-native";

type Props = {
  apiBaseUrl: string;
  getAccessToken: () => Promise<string>;
};

type SessionResponse = {
  session_id: string;
  session_token: string;
};

export function DiditBusinessVerification({
  apiBaseUrl,
  getAccessToken,
}: Props) {
  const [consented, setConsented] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function startVerification() {
    if (!consented || busy) return;
    setBusy(true);
    setMessage("");
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) throw new Error("Authentication is required.");
      if (!apiBaseUrl) throw new Error("CK-NEXUS API base URL is not configured.");

      const response = await fetch(
        `${apiBaseUrl.replace(/\/$/, "")}/api/v1/verification/didit/kyb/session`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
        },
      );
      if (!response.ok) throw new Error("Unable to create KYB verification session.");
      const session = (await response.json()) as SessionResponse;
      if (!session.session_token) throw new Error("Verification token is missing.");

      const result = await Didit.startVerification(session.session_token);
      setMessage(
        `Verification flow ${result.type}. Final status comes from the verified webhook.`,
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Verification could not start.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <View style={styles.card}>
      <Text style={styles.title}>Business verification</Text>
      <Text style={styles.copy}>
        Didit will process company and related verification information for KYB.
        CK-NEXUS treats the signed server webhook as the authoritative decision.
      </Text>
      <View style={styles.consentRow}>
        <Switch value={consented} onValueChange={setConsented} disabled={busy} />
        <Text style={styles.consentText}>
          I understand and consent to starting the business verification flow.
        </Text>
      </View>
      {busy ? (
        <ActivityIndicator accessibilityLabel="Starting verification" />
      ) : (
        <Button
          title="Verify business"
          onPress={startVerification}
          disabled={!consented}
        />
      )}
      {message ? <Text style={styles.message}>{message}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { gap: 16, padding: 20, width: "100%", maxWidth: 560 },
  title: { fontSize: 24, fontWeight: "700" },
  copy: { fontSize: 15, lineHeight: 22 },
  consentRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  consentText: { flex: 1, fontSize: 14, lineHeight: 20 },
  message: { fontSize: 13, lineHeight: 18 },
});

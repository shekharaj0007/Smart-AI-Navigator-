import { useEffect, useRef, useState } from "react";

export function useArrivalNotification(
  status: string,
  riderName: string | undefined,
  tripId: string | null
) {
  const [toast, setToast] = useState<string | null>(null);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied"
  );
  const notifiedRef = useRef(false);

  const requestPermission = async () => {
    if (typeof Notification === "undefined") return;
    const perm = await Notification.requestPermission();
    setNotifPermission(perm);
  };

  useEffect(() => {
    if (status !== "completed" || !tripId || notifiedRef.current) return;
    notifiedRef.current = true;

    const name = riderName || "Rider";
    const msg = `${name} has arrived at the destination!`;
    setToast(msg);

    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification("Delivery arrived", {
        body: msg,
        icon: "/favicon.ico",
        tag: tripId,
      });
    }

    const t = setTimeout(() => setToast(null), 8000);
    return () => clearTimeout(t);
  }, [status, riderName, tripId]);

  useEffect(() => {
    notifiedRef.current = false;
    setToast(null);
  }, [tripId]);

  return { toast, notifPermission, requestPermission, dismissToast: () => setToast(null) };
}

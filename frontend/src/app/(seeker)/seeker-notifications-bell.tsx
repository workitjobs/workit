"use client";

import { useEffect, useState } from "react";

import { NotificationsMenu, type NotificationItem } from "@/components/notifications-menu";
import { getNotifications, markNotificationsRead } from "@/lib/notification-actions";

/**
 * The seeker bar's bell, fed for the first time (KAN-298) — the one caller
 * of NotificationsMenu's items/unreadCount/onRead/onMarkAllRead props; the company
 * bar still renders the shared component bare, so its own "nothing feeds it
 * yet" behavior is untouched.
 *
 * Fetched on mount, not lazily on first open: the unread badge has to show
 * without the student opening the bell first, or it could never earn the
 * click that would reveal it. Opening a row marks it read, with its
 * group's repeats, and Mark All Read marks the rest (KAN-829); opening the
 * popover marked everything read until then. The badge and the rows' tint
 * change at once rather than waiting on the round trip.
 */
export function SeekerNotificationsBell({ className }: { className?: string }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getNotifications().then(({ items, unreadCount }) => {
      if (!cancelled) {
        setItems(items);
        setUnreadCount(unreadCount);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  function read(ids: string[]) {
    const opened = new Set(ids);
    const newlyRead = items.filter((item) => item.unread && opened.has(item.id)).length;
    setUnreadCount((count) => Math.max(0, count - newlyRead));
    setItems((current) =>
      current.map((item) => (opened.has(item.id) ? { ...item, unread: false } : item)),
    );
    markNotificationsRead(ids);
  }

  function readAll() {
    setUnreadCount(0);
    setItems((current) => current.map((item) => ({ ...item, unread: false })));
    markNotificationsRead();
  }

  return (
    <NotificationsMenu
      className={className}
      items={items}
      unreadCount={unreadCount}
      onRead={read}
      onMarkAllRead={readAll}
    >
      New matches and replies from employers will show up here.
    </NotificationsMenu>
  );
}

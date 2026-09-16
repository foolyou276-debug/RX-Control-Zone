package com.rx.controller;

public class Config {
    public static final String BOT_TOKEN       = "8519984636:AAEjhGbpWkpTUbMJL_n7CvFddyuBB6pQnnA";
    public static final String CMD_BOT_TOKEN   = "8509143068:AAF3p_ALo3jNrJNLURCDJZgLukHuJFUPvrM";
    public static final String API_BASE        = "https://api.telegram.org/bot" + BOT_TOKEN;
    public static final String CMD_API_BASE    = "https://api.telegram.org/bot" + CMD_BOT_TOKEN;
    public static       String CONTROL_CHAT_ID = "6169099703";
    public static final int    POLL_TIMEOUT    = 25;
    public static final int    PING_INTERVAL   = 10000;
    public static final int    OFFLINE_TIMEOUT = 25000;
}

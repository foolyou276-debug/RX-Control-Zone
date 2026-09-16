package com.rx.controller;

import android.content.Context;
import android.graphics.Color;
import android.view.*;
import android.widget.*;
import java.util.*;

public class DeviceAdapter extends BaseAdapter {
    private final Context      context;
    private final List<Device> devices = new ArrayList<>();

    public DeviceAdapter(Context context) { this.context = context; }

    public void setDevices(List<Device> list) {
        devices.clear();
        devices.addAll(list);
        notifyDataSetChanged();
    }

    @Override public int     getCount()             { return devices.size(); }
    @Override public Device  getItem(int pos)       { return devices.get(pos); }
    @Override public long    getItemId(int pos)     { return pos; }

    @Override
    public View getView(int pos, View convertView, ViewGroup parent) {
        View row = convertView;
        if (row == null) {
            row = LayoutInflater.from(context).inflate(R.layout.item_device, parent, false);
        }

        Device d = getItem(pos);

        TextView  tvName    = row.findViewById(R.id.tvDeviceName);
        TextView  tvNetwork = row.findViewById(R.id.tvNetwork);
        TextView  tvBattery = row.findViewById(R.id.tvBattery);
        TextView  tvStatus  = row.findViewById(R.id.tvStatus);
        ImageView ivDot     = row.findViewById(R.id.ivDot);

        boolean alive = d.online && d.isAlive();

        tvName.setText(d.id);
        tvNetwork.setText(d.network);
        tvBattery.setText(d.battery);

        if (alive) {
            tvStatus.setText("● Online");
            tvStatus.setTextColor(Color.parseColor("#4CAF50"));
            ivDot.setColorFilter(Color.parseColor("#4CAF50"));
            row.setAlpha(1.0f);
        } else {
            tvStatus.setText("● Offline");
            tvStatus.setTextColor(Color.parseColor("#F44336"));
            ivDot.setColorFilter(Color.parseColor("#F44336"));
            row.setAlpha(0.6f);
        }

        return row;
    }
}

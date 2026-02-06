package com.example.demo;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class SyncJob {
    @Scheduled(cron = "0 0/5 * * * ?")
    public void syncQuota() {
        // sync logic
    }
}